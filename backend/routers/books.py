from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from backend.database import fetch_all, fetch_one, execute_write, transaction, execute_in_transaction
from backend.auth import get_current_admin, get_optional_user
from backend.models import BookCreateRequest, AddCopyRequest

router = APIRouter(prefix="/api/books", tags=["Books & Catalog"])

@router.get("/categories")
def get_categories():
    """Retrieve all categories along with current catalog book counts."""
    query = """
    SELECT 
        c.category_id, 
        c.category_name, 
        c.description,
        COUNT(b.book_id) AS book_count
    FROM categories c
    LEFT JOIN books b ON c.category_id = b.category_id
    GROUP BY c.category_id, c.category_name, c.description
    ORDER BY c.category_name ASC
    """
    return fetch_all(query)

@router.get("")
def list_books(
    search: Optional[str] = Query(None, description="Search query by title, ISBN, or author"),
    category_id: Optional[int] = Query(None, description="Filter by Category ID"),
    available_only: bool = Query(False, description="Filter books with at least 1 available physical copy"),
    sort_by: Optional[str] = Query("title", pattern="^(title|year_desc|year_asc|available)$")
):
    """
    Search and filter catalog books.
    Utilizes SQL View `v_catalog_availability` for high-performance joined results.
    """
    if not isinstance(search, str):
        search = None
    if not isinstance(category_id, int):
        category_id = None
    if not isinstance(available_only, bool):
        available_only = False
    if not isinstance(sort_by, str):
        sort_by = "title"

    base_query = "SELECT * FROM v_catalog_availability WHERE 1=1"
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        base_query += " AND (title LIKE %s OR isbn LIKE %s OR authors LIKE %s OR description LIKE %s)"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if category_id:
        base_query += " AND category_id = %s"
        params.append(category_id)

    if available_only:
        base_query += " AND available_copies > 0"

    # Sorting
    if sort_by == "year_desc":
        base_query += " ORDER BY publication_year DESC NULLS LAST, title ASC"
    elif sort_by == "year_asc":
        base_query += " ORDER BY publication_year ASC NULLS LAST, title ASC"
    elif sort_by == "available":
        base_query += " ORDER BY available_copies DESC, title ASC"
    else:
        base_query += " ORDER BY title ASC"

    # SQLite compatibility: clean NULLS LAST if present on SQLite
    base_query = base_query.replace(" NULLS LAST", "")

    return fetch_all(base_query, tuple(params))

@router.get("/{book_id}")
def get_book_details(book_id: int, current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """
    Fetches full details for a book, including its physical copies, shelf locations,
    active waitlist position, and 'Students Who Borrowed This Also Borrowed' recommendations.
    """
    if not isinstance(current_user, dict):
        current_user = None

    book = fetch_one("SELECT * FROM v_catalog_availability WHERE book_id = %s", (book_id,))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found in library catalog.")

    # 1. Physical Copies inventory
    copies_query = """
    SELECT 
        copy_id, 
        barcode, 
        shelf_location, 
        condition, 
        status
    FROM book_copies
    WHERE book_id = %s
    ORDER BY copy_id ASC
    """
    copies = fetch_all(copies_query, (book_id,))
    book["copies"] = copies

    # 2. Waitlist metrics
    waitlist_count_res = fetch_one(
        "SELECT COUNT(*) AS queue_count FROM waitlist WHERE book_id = %s AND status = 'waiting'", 
        (book_id,)
    )
    book["waitlist_count"] = waitlist_count_res["queue_count"] if waitlist_count_res else 0

    user_waitlist_pos = None
    if current_user:
        user_pos_res = fetch_one("""
        SELECT COUNT(*) + 1 AS position
        FROM waitlist w1
        WHERE w1.book_id = %s AND w1.status = 'waiting'
        AND w1.requested_at <= (
            SELECT w2.requested_at FROM waitlist w2 
            WHERE w2.book_id = %s AND w2.user_id = %s AND w2.status = 'waiting'
            ORDER BY w2.requested_at ASC LIMIT 1
        )
        """, (book_id, book_id, current_user["user_id"]))
        if user_pos_res and user_pos_res.get("position"):
            # Check if user actually has an entry
            user_entry = fetch_one("SELECT status FROM waitlist WHERE book_id = %s AND user_id = %s AND status IN ('waiting', 'notified')", (book_id, current_user["user_id"]))
            if user_entry:
                user_waitlist_pos = {
                    "position": user_pos_res["position"],
                    "status": user_entry["status"]
                }
    book["user_waitlist"] = user_waitlist_pos

    # 3. Recommendation Query: "Students Who Borrowed This Also Borrowed" (Self-Join)
    recs_query = """
    SELECT 
        b.book_id, 
        b.title, 
        b.isbn, 
        b.cover_image_url, 
        c.category_name,
        COUNT(DISTINCT l2.user_id) AS co_borrow_count
    FROM loans l1
    JOIN book_copies bc1 ON l1.copy_id = bc1.copy_id
    JOIN loans l2 ON l1.user_id = l2.user_id AND l1.loan_id != l2.loan_id
    JOIN book_copies bc2 ON l2.copy_id = bc2.copy_id
    JOIN books b ON bc2.book_id = b.book_id
    LEFT JOIN categories c ON b.category_id = c.category_id
    WHERE bc1.book_id = %s AND bc2.book_id != %s
    GROUP BY b.book_id, b.title, b.isbn, b.cover_image_url, c.category_name
    ORDER BY co_borrow_count DESC
    LIMIT 4
    """
    recommendations = fetch_all(recs_query, (book_id, book_id))

    # Fallback to same-category titles if co-borrow count is empty or low
    if len(recommendations) < 3 and book.get("category_id"):
        fallback_query = """
        SELECT 
            b.book_id, 
            b.title, 
            b.isbn, 
            b.cover_image_url, 
            c.category_name,
            0 AS co_borrow_count
        FROM books b
        LEFT JOIN categories c ON b.category_id = c.category_id
        WHERE b.category_id = %s AND b.book_id != %s
        ORDER BY b.publication_year DESC
        LIMIT %s
        """
        needed = 4 - len(recommendations)
        fallbacks = fetch_all(fallback_query, (book["category_id"], book_id, needed))
        existing_ids = {r["book_id"] for r in recommendations}
        for fb in fallbacks:
            if fb["book_id"] not in existing_ids:
                recommendations.append(fb)

    book["recommendations"] = recommendations
    return book

@router.post("", status_code=status.HTTP_201_CREATED)
def create_book(req: BookCreateRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Librarian / Admin only: Adds a new catalog title and authors in a clean transaction.
    """
    # Check ISBN uniqueness
    existing = fetch_one("SELECT book_id FROM books WHERE isbn = %s", (req.isbn,))
    if existing:
        raise HTTPException(status_code=400, detail=f"Book with ISBN '{req.isbn}' already exists in catalog.")

    publisher_id = None
    if req.publisher_name:
        pub = fetch_one("SELECT publisher_id FROM publishers WHERE publisher_name = %s", (req.publisher_name.strip(),))
        if pub:
            publisher_id = pub["publisher_id"]
        else:
            publisher_id = execute_write(
                "INSERT INTO publishers (publisher_name, country) VALUES (%s, %s)",
                (req.publisher_name.strip(), "International")
            )

    with transaction() as conn:
        insert_book_query = """
        INSERT INTO books (
            isbn, title, subtitle, publisher_id, category_id, 
            publication_year, edition, language, pages, description, cover_image_url
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur = execute_in_transaction(
            conn, 
            insert_book_query, 
            (
                req.isbn, req.title, req.subtitle, publisher_id, req.category_id,
                req.publication_year, req.edition, req.language, req.pages,
                req.description, req.cover_image_url
            )
        )
        book_id = cur.lastrowid

        # Insert / link authors
        for author_name in req.authors:
            cleaned_name = author_name.strip()
            if not cleaned_name:
                continue
            cur_auth = execute_in_transaction(conn, "SELECT author_id FROM authors WHERE name = %s", (cleaned_name,))
            row = cur_auth.fetchone()
            if row:
                auth_id = row[0] if isinstance(row, tuple) else row["author_id"]
            else:
                cur_new = execute_in_transaction(conn, "INSERT INTO authors (name) VALUES (%s)", (cleaned_name,))
                auth_id = cur_new.lastrowid
            
            execute_in_transaction(conn, "INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (%s, %s)", (book_id, auth_id))

    return {"message": "Book successfully cataloged.", "book_id": book_id}

@router.post("/{book_id}/copies", status_code=status.HTTP_201_CREATED)
def add_physical_copy(book_id: int, req: AddCopyRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Librarian / Admin only: Registers a new physical copy with barcode and shelf location.
    """
    book = fetch_one("SELECT book_id FROM books WHERE book_id = %s", (book_id,))
    if not book:
        raise HTTPException(status_code=404, detail="Book does not exist.")

    existing_barcode = fetch_one("SELECT copy_id FROM book_copies WHERE barcode = %s", (req.barcode.strip(),))
    if existing_barcode:
        raise HTTPException(status_code=400, detail=f"A physical copy with barcode '{req.barcode}' already exists.")

    copy_id = execute_write(
        "INSERT INTO book_copies (book_id, barcode, shelf_location, condition, status) VALUES (%s, %s, %s, %s, 'available')",
        (book_id, req.barcode.strip(), req.shelf_location.strip(), req.condition)
    )

    return {"message": "Physical copy registered successfully.", "copy_id": copy_id, "barcode": req.barcode}

@router.delete("/{book_id}")
def delete_book(book_id: int, admin: Dict[str, Any] = Depends(get_current_admin)):
    """
    Librarian / Admin only: Deletes a catalog book.
    Triggers DB trigger `trg_book_delete_audit` for automatic audit logging.
    """
    book = fetch_one("SELECT book_id, title FROM books WHERE book_id = %s", (book_id,))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")

    # Prevent deletion if active loans exist
    active_loans = fetch_one("""
    SELECT COUNT(*) AS active_count 
    FROM loans l
    JOIN book_copies bc ON l.copy_id = bc.copy_id
    WHERE bc.book_id = %s AND l.return_date IS NULL
    """, (book_id,))
    if active_loans and active_loans["active_count"] > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete book while physical copies are actively on loan."
        )

    execute_write("DELETE FROM books WHERE book_id = %s", (book_id,))
    return {"message": f"Book '{book['title']}' deleted successfully and recorded in audit log."}
