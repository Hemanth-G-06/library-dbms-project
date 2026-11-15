# 📚 Smart Library Management System (DBMS Project)

A complete, production-ready, full-stack **Smart Library Management System** architected specifically for academic Database Management Systems (DBMS) project evaluation.

The system emphasizes **Third Normal Form (3NF) relational modeling**, **ACID transactions with row-level locking**, **autonomous database triggers**, **aggregated SQL views**, **self-join recommendation algorithms**, and a responsive frontend built strictly with **HTML5, CSS3, and Vanilla JavaScript (ES6+)**.

---

## 🌟 Key DBMS Concepts & Highlights

1. **Third Normal Form (3NF) Normalized Schema:**
   - 13 tables engineered to eliminate data anomalies (insertion, deletion, and update anomalies).
   - Pure separation of catalog entities (`books`), physical inventory (`book_copies`), publishers, categories, authors, and loans.
   - Many-to-Many bridge table (`book_authors`) resolving the relationship between authors and titles.
   - Composite Primary Keys on `book_authors (book_id, author_id)` and `request_votes (request_id, user_id)`.

2. **ACID Checkout Transactions with Concurrency Control:**
   - Book checkout runs inside an isolated transaction (`BEGIN` / `COMMIT` / `ROLLBACK`).
   - Employs row locking (`SELECT ... FOR UPDATE`) to eliminate race conditions on the final available copy.

3. **Autonomous SQL Database Triggers:**
   - **Trigger 1 (`trg_loan_return_waitlist`):** Automated FIFO waitlist processor. Upon book return, checks if students are waiting in queue. If found, automatically reserves the copy and updates the patron's status to `'notified'`; otherwise, returns copy to `'available'`.
   - **Trigger 2 (`trg_loan_fine_calculation`):** Automated overdue fine generation. If a book is returned after its due date, the trigger calculates days overdue and inserts an unpaid fine into `fines` (`DATEDIFF(return_date, due_date) * 1.00`).
   - **Trigger 3A (`trg_fine_waived_audit`):** Tamper-proof audit logging. When a fine is waived by an administrator, automatically writes old and new states in JSON format into `audit_logs`.
   - **Trigger 3B (`trg_book_delete_audit`):** Logs catalog book deletions into `audit_logs`.

4. **Multi-Table Relational Views:**
   - **`v_catalog_availability`:** Joins `books`, `publishers`, `categories`, and aggregates `book_authors` and `book_copies` via subqueries to calculate real-time `total_copies`, `available_copies`, and `reserved_copies` without Cartesian fan-out.
   - **`v_active_loans_summary`:** Comprehensive view tracking student loans, barcode details, due dates, and live overdue day computations.

5. **SQL Self-Join Recommendation Query:**
   - Self-joins historical borrowing data (`loans` ↔ `loans`) to compute *"Students Who Borrowed This Also Borrowed"* recommendations for each catalog item.

6. **Relational Interval Overlap Conflict Validation:**
   - Study room reservations prevent double bookings using mathematical time-interval overlap logic:  
     `start_time < new_end AND end_time > new_start`.

7. **Dual Database Architecture (MySQL + Zero-Config SQLite Fallback):**
   - Standard MySQL 8.0+ DDL scripts (`schema.sql` and `seed.sql`) with foreign keys, checks, triggers, and views.
   - Transparent zero-config fallback to SQLite if MySQL is offline, registering custom functions (`NOW()`, `DATEDIFF()`, `GREATEST()`) so all raw SQL queries execute identically.

---

## 🗄️ Database Schema (13 Normalized Tables)

```
users (user_id PK, library_card_no UNIQUE, full_name, email UNIQUE, password_hash, role, status)
  │
  ├── loans (loan_id PK, copy_id FK, user_id FK, issued_by FK, issue_date, due_date, return_date, status)
  │     └── fines (fine_id PK, loan_id FK UNIQUE, user_id FK, amount, payment_status, paid_date)
  │
  ├── waitlist (waitlist_id PK, book_id FK, user_id FK, requested_at, status)
  ├── room_bookings (booking_id PK, room_id FK, user_id FK, booking_date, start_time, end_time, status)
  ├── book_requests (request_id PK, title, author, isbn, requested_by FK, estimated_price, status)
  │     └── request_votes (request_id FK, user_id FK, PRIMARY KEY (request_id, user_id))
  └── audit_logs (log_id PK, actor_id FK, action_type, target_table, target_record_id, old_value, new_value, timestamp)

categories (category_id PK, category_name UNIQUE, description)
publishers (publisher_id PK, publisher_name UNIQUE, country, website)
authors (author_id PK, name, bio)

books (book_id PK, isbn UNIQUE, title, subtitle, publisher_id FK, category_id FK, pages, publication_year)
  ├── book_authors (book_id FK, author_id FK, PRIMARY KEY (book_id, author_id))
  └── book_copies (copy_id PK, book_id FK, barcode UNIQUE, shelf_location, condition, status)

study_rooms (room_id PK, room_name UNIQUE, capacity, has_whiteboard, has_power_outlets)
```

---

## 🛠️ Technology Stack

- **Frontend:** Pure **HTML5**, **CSS3** (modern Flexbox, CSS Grid, light & dark theme custom properties), and **Vanilla JavaScript (ES6+)** using `fetch()` API. *(No React, Angular, Vue, or Java).*
- **Backend:** **Python (3.10+)**, **FastAPI**, **Uvicorn**, **Pydantic v2**, raw SQL execution layer with transactions and dictionaries.
- **Database:** **MySQL 8.0+** (or SQLite fallback), **PyMySQL**, complete standard DDL & DML scripts.
- **Security:** **JWT (JSON Web Tokens)** with `pyjwt` and password hashing with salted `bcrypt`.

---

## 📂 Project Directory Structure

```
library-dbms-project/
├── schema.sql                     # Full MySQL DDL script (Tables, Foreign Keys, Triggers, Views)
├── seed.sql                       # Full MySQL DML script (16 books, 36 copies, 6 users, loans, fines)
├── requirements.txt               # Python package dependencies
├── .env.example                   # Environment variable template
├── .env                           # Active environment configuration
├── README.md                      # Comprehensive project documentation
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application, CORS, StaticFiles, and Auth endpoints
│   ├── database.py                # Dual MySQL/SQLite raw SQL execution, connection pooling & ACID transactions
│   ├── auth.py                    # JWT token generation, bcrypt password hashing, and role dependencies
│   ├── models.py                  # Pydantic request/response validation schemas
│   └── routers/
│       ├── __init__.py
│       ├── books.py               # Catalog search, details, copies inventory, co-borrow recommendations
│       ├── loans.py               # ACID checkout transaction, returns, overdue calculations
│       ├── features.py            # Fines, FIFO waitlists, study room booking, crowdsourced upvoting
│       └── admin.py               # Top KPI cards, desk operations, tamper-proof audit log viewer
└── frontend/
    ├── index.html                 # Public catalog & discovery page with shelf tracking & recommendations
    ├── login.html                 # Split-screen auth with role indicator & 1-click quick-fill demo buttons
    ├── dashboard.html             # Sidebar SPA dashboard (My Loans, Fines, Rooms, Requests, Admin Desk)
    ├── css/
    │   └── style.css              # Polished CSS design system (Dark/Light mode, badges, cards, tables, modals)
    └── js/
        ├── api.js                 # Centralized fetch client, JWT handling, theme switcher & toast notifications
        ├── app.js                 # Patron dashboard logic, loan returns, fines, room booking & upvoting
        └── admin.js               # Librarian desk: KPI stats, ACID checkout, fine waiving & trigger audit viewer
```

---

## 🚀 Quick Start Guide (Run in 2 Minutes)

### Step 1: Clone or Navigate to the Project Directory
```bash
cd "library dbms project"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Database

#### Option A: Zero-Config Automatic Mode (SQLite)
The system is pre-configured with `DB_ENGINE=sqlite` in `.env`. On first launch, it will **automatically create all 13 tables, compile SQL triggers, build views, and seed 16 books, 36 physical copies, and 6 users**. No database server setup is needed!

#### Option B: MySQL / MariaDB (XAMPP / MySQL Workbench)
If you prefer running against a local or remote MySQL server:
1. Ensure your MySQL server is running on port 3306.
2. Create the database and run the provided scripts:
   ```bash
   mysql -u root -p < schema.sql
   mysql -u root -p < seed.sql
   ```
3. Update `.env`:
   ```ini
   DB_ENGINE=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=smart_library_db
   ```

### Step 4: Start the FastAPI Server
```bash
uvicorn backend.main:app --reload --port 8000
```

### Step 5: Open the Web Application
Open your browser and navigate to:
- **Catalog & Discovery:** `http://localhost:8000/`
- **Login / Register Portal:** `http://localhost:8000/login`
- **Dashboard:** `http://localhost:8000/dashboard`
- **Interactive Swagger API Docs:** `http://localhost:8000/docs`

---

## 🔑 Pre-Seeded Demo Accounts (1-Click Login)

The login page (`login.html`) includes **1-Click Quick-Fill Demo Buttons** for project presentation:

| Role | Name | Email | Password | Library Card # |
|---|---|---|---|---|
| **Librarian (Admin)** | Dr. Eleanor Vance | `admin@library.edu` | `adminpassword123` | `LIB-ADM-001` |
| **Student (Member)** | Alex Rivera | `alex.rivera@student.edu` | `studentpassword123` | `LIB-STU-101` |
| **Student (Member)** | Sarah Chen | `sarah.chen@student.edu` | `studentpassword123` | `LIB-STU-102` |
| **Student (Member)** | Michael Adebayo | `michael.adebayo@student.edu` | `studentpassword123` | `LIB-STU-103` |
| **Student (Member)** | Priya Sharma | `priya.sharma@student.edu` | `studentpassword123` | `LIB-STU-104` |
| **Student (Member)** | David Kim | `david.kim@student.edu` | `studentpassword123` | `LIB-STU-105` |

---

## 🧪 Live DBMS Demonstration Walkthrough

When demonstrating this project to a professor or evaluator, follow these steps:

### 1. Catalog View & Cartesian Fan-Out Prevention
1. Open `http://localhost:8000/`.
2. Notice the live search bar and category filter pills (`Database Systems`, `Operating Systems`, etc.).
3. Click **"View Copies →"** on *Database System Concepts*.
4. Inspect the physical inventory table: shows barcodes (`BC-1001`, `BC-1002`, `BC-1003`), exact shelf locations (`Aisle 1, Shelf A-1`), conditions, and statuses.
5. Scroll down to see **"Students Who Borrowed This Also Borrowed"** recommendations dynamically calculated via the SQL self-join query.

### 2. ACID Checkout Transaction (Row-Level Locking)
1. Log in as **Dr. Eleanor Vance (Admin)**.
2. Navigate to **"Admin & Triggers Desk"**.
3. Under **Quick Issue Desk**, enter:
   - Patron Card: `LIB-STU-101` (Alex Rivera)
   - Barcode: `BC-1001`
   - Loan Duration: `14` days
4. Click **"Execute Issue Transaction"**.
5. The backend starts an ACID transaction:
   - Validates card holder status is `active`.
   - Acquires row lock on `book_copies` where `barcode = 'BC-1001'`.
   - Atomically updates status to `'issued'`.
   - Inserts record into `loans`.
   - Commits the transaction.

### 3. Database Trigger 1 (Automated FIFO Waitlist Queue)
1. Check the waitlist on *Database System Concepts*: Sarah Chen is #1 in queue.
2. In the **Desk Returns Scanner**, enter barcode `BC-1002` (currently on loan) and click **"Process Book Return"**.
3. **Trigger 1 fires instantly:**
   - Detects `return_date` updated on `loans`.
   - Queries `waitlist` for oldest waiting patron for book #1 (Sarah Chen).
   - Automatically marks physical copy `BC-1002` as `'reserved'`.
   - Updates Sarah Chen's queue item to `'notified'`.

### 4. Database Trigger 2 (Automated Overdue Fine Calculation)
1. Notice Loan #2 (Sarah Chen borrowed *Designing Data-Intensive Applications*, due 2026-11-05).
2. Log in as **Sarah Chen** or return the loan via the admin desk.
3. Upon setting `return_date`, **Trigger 2 fires instantly:**
   - Evaluates `return_date > due_date`.
   - Calculates overdue days (e.g., 10 days).
   - Inserts calculated fine ($10.00) into `fines` table with status `'unpaid'`.

### 5. Database Trigger 3A & Tamper-Proof Audit Logging
1. In the **Admin Desk**, locate the **Fines Waiving Desk**.
2. Click **"Waive Fine (Trigger Audit)"** on any unpaid fine.
3. **Trigger 3A fires instantly:**
   - Inserts record into `audit_logs` with `action_type = 'FINE_WAIVED'`.
   - Encodes `old_value` (`{"amount": 5.0, "status": "unpaid"}`) and `new_value` (`{"amount": 5.0, "status": "waived"}`) as JSON.
4. Scroll to the **Tamper-Proof Audit Log Viewer** at the bottom of the page to observe the live audit entry.

### 6. Relational Conflict-Free Room Booking
1. Switch to the **Study Rooms** tab.
2. Select today's date to view the 9 available hourly slots across study rooms.
3. Green slots are available; gray slots are already confirmed.
4. Attempting overlapping reservations triggers instant 409 Conflict rejection:
   `start_time < new_end AND end_time > new_start`.

---

## 📡 REST API Specification

| Category | Method | Endpoint | Description | Access |
|---|---|---|---|---|
| **Auth** | `POST` | `/api/auth/register` | Register student & generate library card | Public |
| **Auth** | `POST` | `/api/auth/login` | Authenticate user & return JWT token | Public |
| **Auth** | `GET` | `/api/auth/me` | Fetch active user profile | Patron |
| **Catalog** | `GET` | `/api/books` | Search catalog with filters & view join | Public |
| **Catalog** | `GET` | `/api/books/categories` | Categories list with book counts | Public |
| **Catalog** | `GET` | `/api/books/{id}` | Book details, copies & co-borrow recs | Public |
| **Catalog** | `POST` | `/api/books` | Add new catalog title & authors | Admin |
| **Catalog** | `POST` | `/api/books/{id}/copies` | Register physical copy with barcode | Admin |
| **Catalog** | `DELETE`| `/api/books/{id}` | Delete catalog title (fires Trigger 3B) | Admin |
| **Circulation**| `POST` | `/api/loans/issue` | ACID transaction book checkout | Admin |
| **Circulation**| `POST` | `/api/loans/return/{id}` | Return book (fires Triggers 1 & 2) | Patron / Admin |
| **Circulation**| `POST` | `/api/loans/return-by-barcode` | Scan barcode to return book | Admin |
| **Circulation**| `GET` | `/api/loans/my-loans` | Patron active & historical loans | Patron |
| **Circulation**| `GET` | `/api/loans/all` | Institutional loans overview | Admin |
| **Fines** | `GET` | `/api/fines/my-fines` | Patron accrued overdue fines | Patron |
| **Fines** | `POST` | `/api/fines/{id}/pay` | Settle overdue fine | Patron |
| **Fines** | `POST` | `/api/fines/{id}/waive` | Waive fine (fires Trigger 3A audit) | Admin |
| **Waitlist** | `POST` | `/api/waitlist/join` | Join FIFO reservation queue | Patron |
| **Waitlist** | `GET` | `/api/waitlist/my-waitlists` | Active waitlist entries & pickup alert | Patron |
| **Rooms** | `GET` | `/api/rooms` | Study rooms list with amenities | Public |
| **Rooms** | `GET` | `/api/rooms/bookings` | Confirmed bookings for date grid | Public |
| **Rooms** | `POST` | `/api/rooms/book` | Interval conflict-free slot booking | Patron |
| **Requests** | `GET` | `/api/requests` | Crowdsourced acquisition requests | Public |
| **Requests** | `POST` | `/api/requests` | Submit book acquisition suggestion | Patron |
| **Requests** | `POST` | `/api/requests/{id}/vote` | Toggle 1-vote upvote (composite PK) | Patron |
| **Admin** | `GET` | `/api/admin/stats` | Institutional KPI aggregate counts | Admin |
| **Admin** | `GET` | `/api/admin/audit-logs`| Real-time trigger audit log records | Admin |

---

## 🎓 Academic Defense Q&A Cheatsheet

- **Q: Why is this schema in 3NF?**  
  **A:**  
  1. *1NF:* All column values are atomic; no comma-separated arrays in normalized tables (authors are separated into an `authors` entity and linked via `book_authors`).  
  2. *2NF:* Every non-key attribute is fully functionally dependent on the primary key (composite key bridge tables like `book_authors` and `request_votes` contain only FK relationships without partial dependencies).  
  3. *3NF:* No transitive dependencies exist (e.g., publisher country belongs in `publishers`, not in `books`; shelf location belongs to physical `book_copies`, not abstract `books`).

- **Q: How does the system prevent checkout race conditions?**  
  **A:** When issuing a book, the backend executes inside an ACID transaction and applies row-level locking (`SELECT copy_id, status FROM book_copies WHERE barcode = ... FOR UPDATE` in MySQL, `BEGIN IMMEDIATE` in SQLite). If another concurrent checkout request attempts to reserve that same copy, it is forced to wait until the lock is released, and availability is re-verified before any status update occurs.

- **Q: How does the automated FIFO waitlist queue work?**  
  **A:** Database Trigger 1 (`trg_loan_return_waitlist`) is configured as an `AFTER UPDATE ON loans`. When a loan is returned (`NEW.return_date IS NOT NULL AND OLD.return_date IS NULL`), the trigger executes entirely within the database engine to query `waitlist` ordered by `requested_at ASC LIMIT 1`. If an entry exists, it sets the copy to `'reserved'` and marks the student's waitlist record as `'notified'`.

---

## 📄 License
Developed for educational DBMS project demonstration purposes. Open source under the MIT License.

