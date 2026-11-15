from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time
from backend.database import fetch_all, fetch_one, execute_write
from backend.auth import get_current_user, get_current_admin
from backend.models import (
    JoinWaitlistRequest, 
    BookRoomRequest, 
    CreateAcquisitionRequest, 
    UpdateRequestStatus
)

router = APIRouter(prefix="/api", tags=["Innovative DBMS Features"])

# ============================================================================
# 1. FINES MANAGEMENT
# ============================================================================

@router.get("/fines/my-fines")
def get_my_fines(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve all fine records (unpaid, paid, waived) for the authenticated member."""
    query = """
    SELECT 
        f.fine_id,
        f.loan_id,
        f.amount,
        f.payment_status,
        f.paid_date,
        b.book_id,
        b.title AS book_title,
        b.cover_image_url,
        l.issue_date,
        l.due_date,
        l.return_date,
        CAST((julianday(COALESCE(l.return_date, datetime('now'))) - julianday(l.due_date)) AS INTEGER) AS overdue_days
    FROM fines f
    JOIN loans l ON f.loan_id = l.loan_id
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    JOIN books b ON bc.book_id = b.book_id
    WHERE f.user_id = %s
    ORDER BY 
        CASE WHEN f.payment_status = 'unpaid' THEN 0 ELSE 1 END,
        f.fine_id DESC
    """
    return fetch_all(query, (current_user["user_id"],))

@router.post("/fines/{fine_id}/pay")
def pay_fine(fine_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Member settles an unpaid overdue fine."""
    fine = fetch_one("SELECT * FROM fines WHERE fine_id = %s", (fine_id,))
    if not fine:
        raise HTTPException(status_code=404, detail="Fine record not found.")

    if current_user["role"] != "admin" and fine["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to pay this fine.")

    if fine["payment_status"] == "paid":
        raise HTTPException(status_code=400, detail="This fine has already been paid.")
    elif fine["payment_status"] == "waived":
        raise HTTPException(status_code=400, detail="This fine was waived by library administration.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_write("UPDATE fines SET payment_status = 'paid', paid_date = %s WHERE fine_id = %s", (now_str, fine_id))
    return {"message": f"Payment of ${fine['amount']:.2f} processed successfully.", "payment_status": "paid", "paid_date": now_str}

@router.post("/fines/{fine_id}/waive")
def waive_fine(fine_id: int, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Librarian / Admin only: Waives an overdue fine.
    Automatically invokes DB Trigger 3A (trg_fine_waived_audit) to record the transaction.
    """
    fine = fetch_one("SELECT * FROM fines WHERE fine_id = %s", (fine_id,))
    if not fine:
        raise HTTPException(status_code=404, detail="Fine record not found.")

    if fine["payment_status"] == "waived":
        raise HTTPException(status_code=400, detail="Fine has already been waived.")

    execute_write("UPDATE fines SET payment_status = 'waived' WHERE fine_id = %s", (fine_id,))
    
    # Verify audit log was triggered
    latest_audit = fetch_one(
        "SELECT * FROM audit_logs WHERE target_table = 'fines' AND target_record_id = %s ORDER BY log_id DESC LIMIT 1",
        (fine_id,)
    )

    return {
        "message": f"Fine #{fine_id} (${fine['amount']:.2f}) successfully waived.",
        "payment_status": "waived",
        "audit_recorded": True if latest_audit else False,
        "audit_log": latest_audit
    }

@router.get("/fines/all")
def get_all_fines(admin: Dict[str, Any] = Depends(get_current_admin)):
    """Librarian / Admin only: View all fines across members."""
    query = """
    SELECT 
        f.fine_id,
        f.loan_id,
        f.user_id,
        u.full_name AS patron_name,
        u.library_card_no,
        u.email AS patron_email,
        b.title AS book_title,
        f.amount,
        f.payment_status,
        f.paid_date,
        l.due_date,
        l.return_date
    FROM fines f
    JOIN users u ON f.user_id = u.user_id
    JOIN loans l ON f.loan_id = l.loan_id
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    JOIN books b ON bc.book_id = b.book_id
    ORDER BY 
        CASE WHEN f.payment_status = 'unpaid' THEN 0 ELSE 1 END,
        f.fine_id DESC
    """
    return fetch_all(query)

# ============================================================================
# 2. FIFO WAITLIST RESERVATION QUEUE
# ============================================================================

@router.post("/waitlist/join", status_code=status.HTTP_201_CREATED)
def join_waitlist(req: JoinWaitlistRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Enrolls patron into the FIFO reservation waitlist for an out-of-stock book."""
    book = fetch_one("SELECT book_id, title FROM books WHERE book_id = %s", (req.book_id,))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")

    # Check if user is already actively waiting
    existing = fetch_one(
        "SELECT waitlist_id, status FROM waitlist WHERE book_id = %s AND user_id = %s AND status IN ('waiting', 'notified')",
        (req.book_id, current_user["user_id"])
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active waitlist reservation for this book.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    waitlist_id = execute_write(
        "INSERT INTO waitlist (book_id, user_id, requested_at, status) VALUES (%s, %s, %s, 'waiting')",
        (req.book_id, current_user["user_id"], now_str)
    )

    # Calculate queue position
    queue_pos_res = fetch_one(
        "SELECT COUNT(*) AS position FROM waitlist WHERE book_id = %s AND status = 'waiting'",
        (req.book_id,)
    )
    position = queue_pos_res["position"] if queue_pos_res else 1

    return {
        "message": f"Successfully joined waitlist for '{book['title']}'.",
        "waitlist_id": waitlist_id,
        "position_in_queue": position
    }

@router.get("/waitlist/my-waitlists")
def get_my_waitlists(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns active queue entries and pickup notifications for the logged-in patron."""
    query = """
    SELECT 
        w.waitlist_id,
        w.book_id,
        b.title AS book_title,
        b.cover_image_url,
        b.isbn,
        w.requested_at,
        w.status,
        (
            SELECT COUNT(*) 
            FROM waitlist w2 
            WHERE w2.book_id = w.book_id 
              AND w2.status = 'waiting' 
              AND w2.requested_at <= w.requested_at
        ) AS current_queue_position
    FROM waitlist w
    JOIN books b ON w.book_id = b.book_id
    WHERE w.user_id = %s AND w.status IN ('waiting', 'notified')
    ORDER BY w.requested_at ASC
    """
    return fetch_all(query, (current_user["user_id"],))

@router.delete("/waitlist/{waitlist_id}")
def leave_waitlist(waitlist_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Patron cancels their waitlist reservation."""
    entry = fetch_one("SELECT * FROM waitlist WHERE waitlist_id = %s", (waitlist_id,))
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found.")
    
    if current_user["role"] != "admin" and entry["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to cancel this reservation.")

    execute_write("DELETE FROM waitlist WHERE waitlist_id = %s", (waitlist_id,))
    return {"message": "Waitlist reservation cancelled successfully."}

# ============================================================================
# 3. STUDY ROOMS & CONFLICT-FREE SLOT BOOKING
# ============================================================================

@router.get("/rooms")
def list_study_rooms():
    """Retrieve all study rooms and their specifications."""
    return fetch_all("SELECT * FROM study_rooms ORDER BY room_id ASC")

@router.get("/rooms/bookings")
def get_room_bookings(date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD")):
    """
    Returns confirmed room bookings for a specific date to populate the interactive slot grid.
    """
    if not isinstance(date_str, str):
        date_str = None
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    query = """
    SELECT 
        rb.booking_id,
        rb.room_id,
        sr.room_name,
        rb.user_id,
        u.full_name AS booked_by_name,
        rb.booking_date,
        rb.start_time,
        rb.end_time,
        rb.status
    FROM room_bookings rb
    JOIN study_rooms sr ON rb.room_id = sr.room_id
    JOIN users u ON rb.user_id = u.user_id
    WHERE rb.booking_date = %s AND rb.status = 'confirmed'
    ORDER BY rb.start_time ASC
    """
    return fetch_all(query, (target_date,))

@router.post("/rooms/book", status_code=status.HTTP_201_CREATED)
def book_study_room(req: BookRoomRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Reserves a study room slot.
    Executes relational time-interval overlap validation:
    `start_time < new_end AND end_time > new_start` to guarantee conflict-free bookings.
    """
    # 1. Verify study room exists
    room = fetch_one("SELECT * FROM study_rooms WHERE room_id = %s", (req.room_id,))
    if not room:
        raise HTTPException(status_code=404, detail="Study room does not exist.")

    # 2. Format times (ensure HH:MM:SS)
    s_time = req.start_time if len(req.start_time) == 8 else f"{req.start_time}:00"
    e_time = req.end_time if len(req.end_time) == 8 else f"{req.end_time}:00"

    if s_time >= e_time:
        raise HTTPException(status_code=400, detail="Start time must precede end time.")

    booking_date_str = str(req.booking_date)

    # 3. DBMS Conflict Validation (Time Interval Overlap)
    conflict_query = """
    SELECT 
        booking_id, 
        start_time, 
        end_time 
    FROM room_bookings
    WHERE room_id = %s 
      AND booking_date = %s 
      AND status = 'confirmed'
      AND (start_time < %s AND end_time > %s)
    LIMIT 1
    """
    conflict = fetch_one(conflict_query, (req.room_id, booking_date_str, e_time, s_time))
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time slot conflict! {room['room_name']} is already reserved between {conflict['start_time']} and {conflict['end_time']}."
        )

    # 4. Insert confirmed booking
    booking_id = execute_write(
        """
        INSERT INTO room_bookings (room_id, user_id, booking_date, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s, 'confirmed')
        """,
        (req.room_id, current_user["user_id"], booking_date_str, s_time, e_time)
    )

    return {
        "message": f"Study room '{room['room_name']}' successfully reserved.",
        "booking_id": booking_id,
        "room_name": room["room_name"],
        "date": booking_date_str,
        "time_slot": f"{s_time} - {e_time}"
    }

@router.get("/rooms/my-bookings")
def get_my_room_bookings(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve all study room reservations made by the logged-in user."""
    query = """
    SELECT 
        rb.booking_id,
        rb.room_id,
        sr.room_name,
        sr.capacity,
        rb.booking_date,
        rb.start_time,
        rb.end_time,
        rb.status
    FROM room_bookings rb
    JOIN study_rooms sr ON rb.room_id = sr.room_id
    WHERE rb.user_id = %s
    ORDER BY rb.booking_date DESC, rb.start_time ASC
    """
    return fetch_all(query, (current_user["user_id"],))

@router.post("/rooms/cancel/{booking_id}")
def cancel_room_booking(booking_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Cancels a room booking."""
    booking = fetch_one("SELECT * FROM room_bookings WHERE booking_id = %s", (booking_id,))
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if current_user["role"] != "admin" and booking["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to cancel this booking.")

    execute_write("UPDATE room_bookings SET status = 'cancelled' WHERE booking_id = %s", (booking_id,))
    return {"message": "Room reservation cancelled successfully."}

# ============================================================================
# 4. CROWDSOURCED BOOK ACQUISITION VOTING BOARD
# ============================================================================

@router.get("/requests")
def list_book_requests(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Lists crowdsourced book acquisition requests ordered by vote count (DESC).
    Annotates whether the currently authenticated student has voted.
    """
    if not isinstance(current_user, dict):
        current_user = None
    user_id = current_user["user_id"] if current_user else 0
    query = """
    SELECT 
        br.request_id,
        br.title,
        br.author,
        br.isbn,
        br.estimated_price,
        br.status,
        br.created_at,
        u.full_name AS requester_name,
        COUNT(rv.user_id) AS vote_count,
        CASE 
            WHEN EXISTS (SELECT 1 FROM request_votes WHERE request_id = br.request_id AND user_id = %s) THEN 1 
            ELSE 0 
        END AS has_voted
    FROM book_requests br
    JOIN users u ON br.requested_by = u.user_id
    LEFT JOIN request_votes rv ON br.request_id = rv.request_id
    GROUP BY br.request_id, br.title, br.author, br.isbn, br.estimated_price, br.status, br.created_at, u.full_name
    ORDER BY 
        CASE WHEN br.status = 'open' THEN 0 WHEN br.status = 'approved' THEN 1 ELSE 2 END,
        vote_count DESC, 
        br.created_at DESC
    """
    return fetch_all(query, (user_id,))

@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_book_request(req: CreateAcquisitionRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Submit a student request for library book acquisition."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req_id = execute_write(
        """
        INSERT INTO book_requests (title, author, isbn, requested_by, estimated_price, status, created_at)
        VALUES (%s, %s, %s, %s, %s, 'open', %s)
        """,
        (req.title.strip(), req.author.strip(), req.isbn, current_user["user_id"], req.estimated_price, now_str)
    )

    # Automatically cast 1st vote by requester
    execute_write("INSERT OR IGNORE INTO request_votes (request_id, user_id, voted_at) VALUES (%s, %s, %s)", (req_id, current_user["user_id"], now_str))

    return {"message": "Book acquisition request submitted for community voting.", "request_id": req_id}

@router.post("/requests/{request_id}/vote")
def toggle_request_vote(request_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Toggles upvote for a book request (1 vote per student enforced via composite primary key).
    """
    req = fetch_one("SELECT request_id, title FROM book_requests WHERE request_id = %s", (request_id,))
    if not req:
        raise HTTPException(status_code=404, detail="Book request not found.")

    existing_vote = fetch_one(
        "SELECT * FROM request_votes WHERE request_id = %s AND user_id = %s",
        (request_id, current_user["user_id"])
    )

    if existing_vote:
        # Un-vote
        execute_write("DELETE FROM request_votes WHERE request_id = %s AND user_id = %s", (request_id, current_user["user_id"]))
        voted = False
        msg = "Vote removed."
    else:
        # Vote
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_write(
            "INSERT INTO request_votes (request_id, user_id, voted_at) VALUES (%s, %s, %s)",
            (request_id, current_user["user_id"], now_str)
        )
        voted = True
        msg = "Upvote registered."

    total_votes = fetch_one("SELECT COUNT(*) AS cnt FROM request_votes WHERE request_id = %s", (request_id,))["cnt"]
    return {"message": msg, "has_voted": voted, "total_votes": total_votes}

@router.patch("/requests/{request_id}/status")
def update_request_status(
    request_id: int, 
    status_body: UpdateRequestStatus, 
    admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Librarian / Admin only: Approves or marks book acquisition request as purchased."""
    req = fetch_one("SELECT * FROM book_requests WHERE request_id = %s", (request_id,))
    if not req:
        raise HTTPException(status_code=404, detail="Book request not found.")

    execute_write("UPDATE book_requests SET status = %s WHERE request_id = %s", (status_body.status, request_id))
    return {"message": f"Request status updated to '{status_body.status}'.", "status": status_body.status}
