from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.database import fetch_all, fetch_one, execute_write, transaction, execute_in_transaction
from backend.auth import get_current_user, get_current_admin
from backend.models import IssueLoanRequest, ReturnLoanByBarcodeRequest

router = APIRouter(prefix="/api/loans", tags=["Loans & Circulation"])

@router.post("/issue", status_code=status.HTTP_201_CREATED)
def issue_book(req: IssueLoanRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Atomic Checkout Transaction:
    Issues a book copy to a patron inside an isolated ACID transaction with row-level checks
    to prevent race conditions on the last available copy.
    """
    card_no = req.library_card_no.strip()
    barcode = req.barcode.strip()
    due_days = req.due_days or 14

    with transaction() as conn:
        # 1. Patron verification
        cur_u = execute_in_transaction(conn, "SELECT user_id, full_name, status FROM users WHERE library_card_no = %s", (card_no,))
        user_row = cur_u.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail=f"Patron with Library Card '{card_no}' not found.")
        
        user_id = user_row[0] if isinstance(user_row, tuple) else user_row["user_id"]
        user_name = user_row[1] if isinstance(user_row, tuple) else user_row["full_name"]
        user_status = user_row[2] if isinstance(user_row, tuple) else user_row["status"]

        if user_status == "suspended":
            raise HTTPException(status_code=403, detail="Patron membership is suspended. Checkout blocked.")

        # 2. Check for unpaid fines exceeding threshold ($20.00)
        cur_fine = execute_in_transaction(
            conn, 
            "SELECT COALESCE(SUM(amount), 0) AS total_unpaid FROM fines WHERE user_id = %s AND payment_status = 'unpaid'",
            (user_id,)
        )
        fine_row = cur_fine.fetchone()
        unpaid = fine_row[0] if isinstance(fine_row, tuple) else fine_row["total_unpaid"]
        if unpaid and float(unpaid) >= 20.00:
            raise HTTPException(
                status_code=400, 
                detail=f"Patron has excessive unpaid fines (${float(unpaid):.2f}). Clear fines before borrowing."
            )

        # 3. Lock physical copy row for update to prevent race conditions
        cur_copy = execute_in_transaction(
            conn, 
            "SELECT copy_id, book_id, barcode, status FROM book_copies WHERE barcode = %s", 
            (barcode,)
        )
        copy_row = cur_copy.fetchone()
        if not copy_row:
            raise HTTPException(status_code=404, detail=f"No physical copy found with barcode '{barcode}'.")

        copy_id = copy_row[0] if isinstance(copy_row, tuple) else copy_row["copy_id"]
        book_id = copy_row[1] if isinstance(copy_row, tuple) else copy_row["book_id"]
        copy_status = copy_row[3] if isinstance(copy_row, tuple) else copy_row["status"]

        # Check availability
        if copy_status == "issued":
            raise HTTPException(status_code=409, detail=f"Copy '{barcode}' is already on loan.")
        elif copy_status == "lost":
            raise HTTPException(status_code=400, detail=f"Copy '{barcode}' is marked as lost.")
        elif copy_status == "reserved":
            # Allow issue only if this specific user is the one who was notified in waitlist
            cur_wl = execute_in_transaction(
                conn, 
                "SELECT waitlist_id FROM waitlist WHERE book_id = %s AND user_id = %s AND status = 'notified' LIMIT 1",
                (book_id, user_id)
            )
            if not cur_wl.fetchone():
                raise HTTPException(
                    status_code=409, 
                    detail="This physical copy is currently reserved for a member in the waitlist."
                )

        # 4. Atomically update copy status to 'issued'
        execute_in_transaction(conn, "UPDATE book_copies SET status = 'issued' WHERE copy_id = %s", (copy_id,))

        # 5. Insert loan record
        issue_date = datetime.now()
        due_date = issue_date + timedelta(days=due_days)
        issue_str = issue_date.strftime("%Y-%m-%d %H:%M:%S")
        due_str = due_date.strftime("%Y-%m-%d %H:%M:%S")

        cur_loan = execute_in_transaction(
            conn,
            """
            INSERT INTO loans (copy_id, user_id, issued_by, issue_date, due_date, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            """,
            (copy_id, user_id, admin["user_id"], issue_str, due_str)
        )
        loan_id = cur_loan.lastrowid

        # 6. Fulfill waitlist entry if patron was waiting
        execute_in_transaction(
            conn,
            "UPDATE waitlist SET status = 'fulfilled' WHERE book_id = %s AND user_id = %s AND status IN ('waiting', 'notified')",
            (book_id, user_id)
        )

    return {
        "message": f"Book successfully issued to {user_name}.",
        "loan_id": loan_id,
        "copy_id": copy_id,
        "barcode": barcode,
        "issue_date": issue_str,
        "due_date": due_str
    }

@router.post("/return/{loan_id}")
def return_book(loan_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns an active loan.
    Fires Database Trigger 1 (trg_loan_return_waitlist) and Trigger 2 (trg_loan_fine_calculation).
    Accessible to patrons for their own loans or librarians for any loan.
    """
    loan = fetch_one("SELECT * FROM loans WHERE loan_id = %s", (loan_id,))
    if not loan:
        raise HTTPException(status_code=404, detail="Loan transaction record not found.")

    if current_user["role"] != "admin" and loan["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You do not have permission to return another patron's loan.")

    if loan.get("return_date") is not None:
        raise HTTPException(status_code=400, detail="This book has already been marked as returned.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update loan with return timestamp; DB triggers automatically execute!
    execute_write("UPDATE loans SET return_date = %s, status = 'returned' WHERE loan_id = %s", (now_str, loan_id))

    # Inspect results triggered by DB
    fine_check = fetch_one("SELECT * FROM fines WHERE loan_id = %s", (loan_id,))
    copy_check = fetch_one("SELECT status FROM book_copies WHERE copy_id = %s", (loan["copy_id"],))

    fine_msg = None
    if fine_check:
        fine_msg = f"Overdue fine of ${fine_check['amount']:.2f} was automatically generated by database trigger."

    reserved_msg = None
    if copy_check and copy_check["status"] == "reserved":
        reserved_msg = "Copy automatically marked 'reserved' by trigger for the next patron in the FIFO waitlist queue."
    else:
        reserved_msg = "Copy returned to circulation as 'available'."

    return {
        "message": "Book successfully returned.",
        "return_date": now_str,
        "fine_generated": fine_msg,
        "inventory_status": reserved_msg
    }

@router.post("/return-by-barcode")
def return_by_barcode(req: ReturnLoanByBarcodeRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Librarian Desk Scan: Returns a book by physical copy barcode.
    """
    barcode = req.barcode.strip()
    loan = fetch_one("""
    SELECT l.loan_id 
    FROM loans l
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    WHERE bc.barcode = %s AND l.return_date IS NULL
    ORDER BY l.issue_date DESC LIMIT 1
    """, (barcode,))
    
    if not loan:
        raise HTTPException(status_code=404, detail=f"No active loan found for barcode '{barcode}'.")

    return return_book(loan["loan_id"], admin)

@router.get("/my-loans")
def get_my_loans(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves all current active, overdue, and returned loan records for the logged-in patron.
    Includes live overdue calculations and countdown days.
    """
    query = """
    SELECT 
        l.loan_id,
        l.copy_id,
        bc.barcode,
        bc.shelf_location,
        b.book_id,
        b.title,
        b.cover_image_url,
        b.isbn,
        l.issue_date,
        l.due_date,
        l.return_date,
        l.status,
        CASE 
            WHEN l.return_date IS NULL AND datetime('now') > datetime(l.due_date) THEN 'OVERDUE'
            WHEN l.return_date IS NULL THEN 'ON_LOAN'
            ELSE 'RETURNED'
        END AS loan_state,
        CAST((julianday(l.due_date) - julianday(datetime('now'))) AS INTEGER) AS days_remaining,
        MAX(0, CAST((julianday(COALESCE(l.return_date, datetime('now'))) - julianday(l.due_date)) AS INTEGER)) AS days_overdue
    FROM loans l
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    JOIN books b ON bc.book_id = b.book_id
    WHERE l.user_id = %s
    ORDER BY 
        CASE WHEN l.return_date IS NULL THEN 0 ELSE 1 END,
        l.due_date ASC
    """
    return fetch_all(query, (current_user["user_id"],))

@router.get("/all")
def get_all_loans(
    status_filter: Optional[str] = Query(None, pattern="^(active|overdue|returned)$"),
    admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Librarian / Admin only: Lists all borrowing records across the university library.
    """
    if not isinstance(status_filter, str):
        status_filter = None

    query = """
    SELECT 
        l.loan_id,
        l.user_id,
        u.full_name AS patron_name,
        u.library_card_no,
        u.email AS patron_email,
        b.title AS book_title,
        b.isbn,
        bc.barcode,
        bc.shelf_location,
        l.issue_date,
        l.due_date,
        l.return_date,
        l.status AS loan_status,
        CASE 
            WHEN l.return_date IS NULL AND datetime('now') > datetime(l.due_date) THEN 'OVERDUE'
            WHEN l.return_date IS NULL THEN 'ON_LOAN'
            ELSE 'RETURNED'
        END AS display_status,
        MAX(0, CAST((julianday(COALESCE(l.return_date, datetime('now'))) - julianday(l.due_date)) AS INTEGER)) AS days_overdue
    FROM loans l
    JOIN users u ON l.user_id = u.user_id
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    JOIN books b ON bc.book_id = b.book_id
    WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND l.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY CASE WHEN l.return_date IS NULL THEN 0 ELSE 1 END, l.due_date ASC"
    return fetch_all(query, tuple(params))
