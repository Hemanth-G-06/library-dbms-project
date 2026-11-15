import os
import re
import json
import sqlite3
import pymysql
import pymysql.cursors
from datetime import datetime, date
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Load environment configuration
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_ENGINE = os.getenv("DB_ENGINE", "mysql").lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "smart_library_db")

raw_sqlite_path = os.getenv("SQLITE_PATH", "smart_library.db")
if not os.path.isabs(raw_sqlite_path):
    SQLITE_PATH = os.path.join(PROJECT_ROOT, raw_sqlite_path)
else:
    SQLITE_PATH = raw_sqlite_path

CURRENT_ENGINE = "sqlite"

def test_mysql_connection() -> bool:
    """Check if MySQL is reachable with current credentials."""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False

# Determine active database engine
if DB_ENGINE == "mysql" and test_mysql_connection():
    CURRENT_ENGINE = "mysql"
    print(f"[*] Database: Connected to MySQL ({MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE})")
else:
    CURRENT_ENGINE = "sqlite"
    if DB_ENGINE == "mysql":
        print("[!] Notice: MySQL host unreachable on port 3306. Automatically falling back to SQLite for zero-friction local execution.")
    print(f"[*] Database: Running with SQLite engine at: {SQLITE_PATH}")

def _sqlite_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _sqlite_datediff(d1, d2) -> int:
    if not d1 or not d2:
        return 0
    try:
        if isinstance(d1, (datetime, date)):
            d1_date = d1 if isinstance(d1, date) else d1.date()
        else:
            d1_date = datetime.fromisoformat(str(d1).replace("Z", "").split(".")[0].replace(" ", "T")).date()
        
        if isinstance(d2, (datetime, date)):
            d2_date = d2 if isinstance(d2, date) else d2.date()
        else:
            d2_date = datetime.fromisoformat(str(d2).replace("Z", "").split(".")[0].replace(" ", "T")).date()
        return (d1_date - d2_date).days
    except Exception:
        return 0

def _sqlite_greatest(*args):
    return max(args)

def _sqlite_least(*args):
    return min(args)

def _sqlite_json_object(*args):
    """Fallback json_object implementation for SQLite."""
    obj = {}
    for i in range(0, len(args), 2):
        if i + 1 < len(args):
            obj[str(args[i])] = args[i + 1]
    return json.dumps(obj)

def get_sqlite_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.create_function("NOW", 0, _sqlite_now)
    conn.create_function("DATEDIFF", 2, _sqlite_datediff)
    conn.create_function("GREATEST", -1, _sqlite_greatest)
    conn.create_function("LEAST", -1, _sqlite_least)
    try:
        conn.create_function("JSON_OBJECT", -1, _sqlite_json_object)
    except Exception:
        pass
    return conn

def get_mysql_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        charset="utf8mb4"
    )

def adapt_sql(query: str) -> str:
    """
    Translates standard queries between MySQL and SQLite syntax if running SQLite.
    Replaces %s placeholders with ? and adjusts GROUP_CONCAT syntax.
    """
    if CURRENT_ENGINE == "mysql":
        return query
    
    # In SQLite, convert %s to ?
    # Be careful not to replace % inside string literals or LIKE clauses like '%abc%'
    # Replace lone %s with ?
    query = re.sub(r'(?<!%)(%s)', '?', query)
    
    # Replace MySQL GROUP_CONCAT with SEPARATOR to SQLite GROUP_CONCAT
    # MySQL: GROUP_CONCAT(DISTINCT a.name ORDER BY a.name SEPARATOR ', ')
    # SQLite: GROUP_CONCAT(DISTINCT a.name)
    query = re.sub(
        r"GROUP_CONCAT\s*\(\s*DISTINCT\s+([a-zA-Z0-9_\.]+)\s+ORDER\s+BY\s+[a-zA-Z0-9_\.]+\s+SEPARATOR\s+['\"][^'\"]*['\"]\s*\)",
        r"GROUP_CONCAT(DISTINCT \1)",
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r"GROUP_CONCAT\s*\(\s*([a-zA-Z0-9_\.]+)\s+SEPARATOR\s+['\"][^'\"]*['\"]\s*\)",
        r"GROUP_CONCAT(\1)",
        query,
        flags=re.IGNORECASE
    )
    return query

def fetch_all(query: str, params: Any = None) -> List[Dict[str, Any]]:
    """Execute raw SQL query and return all rows as list of dicts."""
    query = adapt_sql(query)
    if CURRENT_ENGINE == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

def fetch_one(query: str, params: Any = None) -> Optional[Dict[str, Any]]:
    """Execute raw SQL query and return single row as dict or None."""
    query = adapt_sql(query)
    if CURRENT_ENGINE == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

def execute_write(query: str, params: Any = None) -> int:
    """Execute INSERT/UPDATE/DELETE and return lastrowid or affected rows."""
    query = adapt_sql(query)
    if CURRENT_ENGINE == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                last_id = cursor.lastrowid
            conn.commit()
            return last_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

@contextmanager
def transaction():
    """
    ACID Transaction context manager providing an isolated connection.
    Commits on successful completion of the block, rolls back on exception.
    """
    if CURRENT_ENGINE == "mysql":
        conn = get_mysql_connection()
        conn.begin()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def execute_in_transaction(conn, query: str, params: Any = None):
    """Executes a query inside an existing transaction connection."""
    adapted = adapt_sql(query)
    if CURRENT_ENGINE == "mysql":
        with conn.cursor() as cursor:
            cursor.execute(adapted, params or ())
            return cursor
    else:
        cursor = conn.cursor()
        cursor.execute(adapted, params or ())
        return cursor

def init_db():
    """
    Initializes database schema, triggers, views and seeds if needed.
    Runs automatically on FastAPI application startup.
    """
    if CURRENT_ENGINE == "sqlite":
        _init_sqlite()
    else:
        # If running MySQL, verify database and tables exist
        try:
            res = fetch_one("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = %s", (MYSQL_DATABASE,))
            if not res or res["cnt"] == 0:
                print("[*] MySQL tables empty. Running schema.sql and seed.sql...")
                _run_mysql_scripts()
        except Exception as e:
            print(f"[!] MySQL check error: {e}")

def _init_sqlite():
    """Builds normalized 3NF tables, triggers, views and seed records in SQLite."""
    conn = get_sqlite_connection()
    try:
        # Check if tables already exist
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cur.fetchone() is not None

        if not table_exists:
            print("[*] Initializing SQLite database schema, triggers, and views...")
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_card_no TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                phone TEXT,
                role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin', 'member')),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'suspended')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS publishers (
                publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
                publisher_name TEXT NOT NULL UNIQUE,
                country TEXT,
                website TEXT
            );

            CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                subtitle TEXT,
                publisher_id INTEGER REFERENCES publishers(publisher_id) ON UPDATE CASCADE ON DELETE SET NULL,
                category_id INTEGER NOT NULL REFERENCES categories(category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                publication_year INTEGER,
                edition TEXT,
                language TEXT NOT NULL DEFAULT 'English',
                pages INTEGER CHECK(pages IS NULL OR pages > 0),
                description TEXT,
                cover_image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS authors (
                author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                bio TEXT
            );

            CREATE TABLE IF NOT EXISTS book_authors (
                book_id INTEGER NOT NULL REFERENCES books(book_id) ON UPDATE CASCADE ON DELETE CASCADE,
                author_id INTEGER NOT NULL REFERENCES authors(author_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                PRIMARY KEY (book_id, author_id)
            );

            CREATE TABLE IF NOT EXISTS book_copies (
                copy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(book_id) ON UPDATE CASCADE ON DELETE CASCADE,
                barcode TEXT NOT NULL UNIQUE,
                shelf_location TEXT NOT NULL,
                condition TEXT NOT NULL DEFAULT 'good' CHECK(condition IN ('new', 'good', 'damaged')),
                status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'issued', 'reserved', 'lost'))
            );

            CREATE TABLE IF NOT EXISTS loans (
                loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                copy_id INTEGER NOT NULL REFERENCES book_copies(copy_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                issued_by INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                issue_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP NOT NULL,
                return_date TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'returned', 'overdue'))
            );

            CREATE TABLE IF NOT EXISTS fines (
                fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL UNIQUE REFERENCES loans(loan_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                amount REAL NOT NULL DEFAULT 0.0 CHECK(amount >= 0.0),
                payment_status TEXT NOT NULL DEFAULT 'unpaid' CHECK(payment_status IN ('unpaid', 'paid', 'waived')),
                paid_date TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS waitlist (
                waitlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(book_id) ON UPDATE CASCADE ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
                requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting', 'notified', 'expired', 'fulfilled'))
            );

            CREATE TABLE IF NOT EXISTS study_rooms (
                room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT NOT NULL UNIQUE,
                capacity INTEGER NOT NULL DEFAULT 4 CHECK(capacity > 0),
                has_whiteboard INTEGER NOT NULL DEFAULT 1,
                has_power_outlets INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS room_bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES study_rooms(room_id) ON UPDATE CASCADE ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
                booking_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'cancelled')),
                CHECK(start_time < end_time)
            );

            CREATE TABLE IF NOT EXISTS book_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT,
                requested_by INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
                estimated_price REAL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'approved', 'purchased')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS request_votes (
                request_id INTEGER NOT NULL REFERENCES book_requests(request_id) ON UPDATE CASCADE ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
                voted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (request_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
                action_type TEXT NOT NULL,
                target_table TEXT NOT NULL,
                target_record_id INTEGER NOT NULL,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            -- Indexes for high performance querying
            CREATE INDEX IF NOT EXISTS idx_users_card ON users(library_card_no);
            CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
            CREATE INDEX IF NOT EXISTS idx_copies_barcode ON book_copies(barcode);
            CREATE INDEX IF NOT EXISTS idx_loans_user ON loans(user_id);
            CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
            CREATE INDEX IF NOT EXISTS idx_waitlist_status ON waitlist(status);

            -- View: v_catalog_availability
            DROP VIEW IF EXISTS v_catalog_availability;
            CREATE VIEW v_catalog_availability AS
            SELECT 
                b.book_id,
                b.isbn,
                b.title,
                b.subtitle,
                b.publication_year,
                b.edition,
                b.language,
                b.pages,
                b.description,
                b.cover_image_url,
                p.publisher_id,
                p.publisher_name,
                p.country AS publisher_country,
                c.category_id,
                c.category_name,
                COALESCE(auth.authors, 'Unknown Author') AS authors,
                COALESCE(auth.author_ids, '') AS author_ids,
                COALESCE(cp.total_copies, 0) AS total_copies,
                COALESCE(cp.available_copies, 0) AS available_copies,
                COALESCE(cp.reserved_copies, 0) AS reserved_copies,
                COALESCE(cp.issued_copies, 0) AS issued_copies
            FROM books b
            LEFT JOIN publishers p ON b.publisher_id = p.publisher_id
            LEFT JOIN categories c ON b.category_id = c.category_id
            LEFT JOIN (
                SELECT 
                    ba.book_id,
                    GROUP_CONCAT(DISTINCT a.name) AS authors,
                    GROUP_CONCAT(DISTINCT a.author_id) AS author_ids
                FROM book_authors ba
                JOIN authors a ON ba.author_id = a.author_id
                GROUP BY ba.book_id
            ) auth ON b.book_id = auth.book_id
            LEFT JOIN (
                SELECT 
                    book_id,
                    COUNT(copy_id) AS total_copies,
                    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) AS available_copies,
                    SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) AS reserved_copies,
                    SUM(CASE WHEN status = 'issued' THEN 1 ELSE 0 END) AS issued_copies
                FROM book_copies
                GROUP BY book_id
            ) cp ON b.book_id = cp.book_id;

            -- View: v_active_loans_summary
            DROP VIEW IF EXISTS v_active_loans_summary;
            CREATE VIEW v_active_loans_summary AS
            SELECT 
                l.loan_id,
                l.user_id,
                u.full_name AS student_name,
                u.library_card_no,
                u.email AS student_email,
                b.book_id,
                b.title AS book_title,
                b.isbn,
                bc.copy_id,
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
            JOIN books b ON bc.book_id = b.book_id;

            -- Trigger 1: Automated FIFO Waitlist Processor on Loan Return
            DROP TRIGGER IF EXISTS trg_loan_return_waitlist;
            CREATE TRIGGER trg_loan_return_waitlist
            AFTER UPDATE OF return_date ON loans
            FOR EACH ROW
            WHEN NEW.return_date IS NOT NULL AND OLD.return_date IS NULL
            BEGIN
                UPDATE book_copies 
                SET status = CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM waitlist w 
                        JOIN book_copies bc ON bc.book_id = w.book_id 
                        WHERE bc.copy_id = NEW.copy_id AND w.status = 'waiting'
                    ) THEN 'reserved' 
                    ELSE 'available' 
                END
                WHERE copy_id = NEW.copy_id;

                UPDATE waitlist
                SET status = 'notified'
                WHERE waitlist_id = (
                    SELECT w.waitlist_id FROM waitlist w
                    JOIN book_copies bc ON bc.book_id = w.book_id
                    WHERE bc.copy_id = NEW.copy_id AND w.status = 'waiting'
                    ORDER BY w.requested_at ASC
                    LIMIT 1
                );
            END;

            -- Trigger 2: Automated Overdue Fine Generation on Return
            DROP TRIGGER IF EXISTS trg_loan_fine_calculation;
            CREATE TRIGGER trg_loan_fine_calculation
            AFTER UPDATE OF return_date ON loans
            FOR EACH ROW
            WHEN NEW.return_date IS NOT NULL AND OLD.return_date IS NULL AND julianday(NEW.return_date) > julianday(NEW.due_date)
            BEGIN
                INSERT INTO fines (loan_id, user_id, amount, payment_status, paid_date)
                VALUES (
                    NEW.loan_id, 
                    NEW.user_id, 
                    ROUND((julianday(NEW.return_date) - julianday(NEW.due_date)) * 1.0, 2), 
                    'unpaid', 
                    NULL
                );
            END;

            -- Trigger 3A: Audit Logging for Fine Waiving
            DROP TRIGGER IF EXISTS trg_fine_waived_audit;
            CREATE TRIGGER trg_fine_waived_audit
            AFTER UPDATE OF payment_status ON fines
            FOR EACH ROW
            WHEN NEW.payment_status = 'waived' AND OLD.payment_status != 'waived'
            BEGIN
                INSERT INTO audit_logs (actor_id, action_type, target_table, target_record_id, old_value, new_value, timestamp)
                VALUES (
                    NEW.user_id,
                    'FINE_WAIVED',
                    'fines',
                    NEW.fine_id,
                    json_object('amount', OLD.amount, 'status', OLD.payment_status),
                    json_object('amount', NEW.amount, 'status', NEW.payment_status),
                    datetime('now')
                );
            END;

            -- Trigger 3B: Audit Logging for Book Deletions
            DROP TRIGGER IF EXISTS trg_book_delete_audit;
            CREATE TRIGGER trg_book_delete_audit
            AFTER DELETE ON books
            FOR EACH ROW
            BEGIN
                INSERT INTO audit_logs (actor_id, action_type, target_table, target_record_id, old_value, new_value, timestamp)
                VALUES (
                    NULL,
                    'BOOK_DELETED',
                    'books',
                    OLD.book_id,
                    json_object('title', OLD.title, 'isbn', OLD.isbn),
                    NULL,
                    datetime('now')
                );
            END;
            """)
            conn.commit()
            _seed_sqlite(conn)
    finally:
        conn.close()

def _seed_sqlite(conn):
    """Populates SQLite with the realistic seed dataset."""
    print("[*] Populating SQLite database with seed dataset (16 books, 36 copies, 6 users, loans, fines, rooms)...")
    cur = conn.cursor()
    
    # 1. Users
    users = [
        (1, 'LIB-ADM-001', 'Dr. Eleanor Vance', 'admin@library.edu', '$2b$12$OyGweI82sDmXEf9b7I2gleB5c9pk2jVReYXnoerdmQy2.wDi3tYq2', '+1-555-0100', 'admin', 'active', '2025-01-01 08:00:00'),
        (2, 'LIB-STU-101', 'Alex Rivera', 'alex.rivera@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0101', 'member', 'active', '2025-01-10 09:30:00'),
        (3, 'LIB-STU-102', 'Sarah Chen', 'sarah.chen@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0102', 'member', 'active', '2025-01-12 11:15:00'),
        (4, 'LIB-STU-103', 'Michael Adebayo', 'michael.adebayo@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0103', 'member', 'active', '2025-01-15 14:00:00'),
        (5, 'LIB-STU-104', 'Priya Sharma', 'priya.sharma@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0104', 'member', 'active', '2025-01-18 10:45:00'),
        (6, 'LIB-STU-105', 'David Kim', 'david.kim@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0105', 'member', 'active', '2025-01-20 16:20:00')
    ]
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", users)

    # 2. Categories
    categories = [
        (1, 'Database Systems', 'Relational design, normalization, SQL, indexing, and transactions.'),
        (2, 'Software Engineering', 'System architecture, design patterns, clean code, and testing.'),
        (3, 'Algorithms & Data Structures', 'Algorithmic paradigms, complexity analysis, and graph theory.'),
        (4, 'Operating Systems', 'Kernel architecture, virtualization, concurrency, and file systems.'),
        (5, 'Computer Networks', 'Protocol layers, TCP/IP, network security, and routing.'),
        (6, 'Artificial Intelligence', 'Machine learning, neural networks, NLP, and heuristics.')
    ]
    cur.executemany("INSERT INTO categories VALUES (?,?,?)", categories)

    # 3. Publishers
    publishers = [
        (1, 'McGraw-Hill Education', 'United States', 'https://www.mheducation.com'),
        (2, "O'Reilly Media", 'United States', 'https://www.oreilly.com'),
        (3, 'MIT Press', 'United States', 'https://mitpress.mit.edu'),
        (4, 'Prentice Hall', 'United States', 'https://www.pearson.com'),
        (5, 'John Wiley & Sons', 'United States', 'https://www.wiley.com'),
        (6, 'Pearson Education', 'United Kingdom', 'https://www.pearson.com'),
        (7, 'Addison-Wesley Professional', 'United States', 'https://www.informit.com'),
        (8, 'No Starch Press', 'United States', 'https://nostarch.com')
    ]
    cur.executemany("INSERT INTO publishers VALUES (?,?,?,?)", publishers)

    # 4. Authors
    authors = [
        (1, 'Abraham Silberschatz', 'Professor of Computer Science at Yale University.'),
        (2, 'Henry F. Korth', 'Professor of Computer Science and Engineering at Lehigh University.'),
        (3, 'S. Sudarshan', 'Professor of Computer Science and Engineering at IIT Bombay.'),
        (4, 'Martin Kleppmann', 'Associate Professor in Distributed Systems at Cambridge.'),
        (5, 'Thomas H. Cormen', 'Professor of Computer Science at Dartmouth College.'),
        (6, 'Charles E. Leiserson', 'Professor of Computer Science and Engineering at MIT.'),
        (7, 'Ronald L. Rivest', 'Professor of Computer Science at MIT and RSA co-inventor.'),
        (8, 'Clifford Stein', 'Professor of Industrial Engineering and Operations Research at Columbia.'),
        (9, 'Robert C. Martin', 'Renowned software engineer widely known as "Uncle Bob".'),
        (10, 'Peter B. Galvin', 'Chief Technologist at Corporate Technologies.'),
        (11, 'James F. Kurose', 'Distinguished Professor Emeritus at UMass Amherst.'),
        (12, 'Keith W. Ross', 'Professor of Computer Science and Engineering at NYU Tandon.'),
        (13, 'Stuart Russell', 'Professor of Computer Science at UC Berkeley.'),
        (14, 'Peter Norvig', 'Director of Research at Google.'),
        (15, 'Andrew S. Tanenbaum', 'Creator of the MINIX operating system.'),
        (16, 'David Thomas', 'Author of The Pragmatic Programmer.'),
        (17, 'Andrew Hunt', 'Co-author of The Pragmatic Programmer.'),
        (18, 'Ian Goodfellow', 'Research scientist specializing in deep generative models.')
    ]
    cur.executemany("INSERT INTO authors VALUES (?,?,?)", authors)

    # 5. Books
    books = [
        (1, '978-0078022159', 'Database System Concepts', 'Complete Fundamentals of Relational Systems & SQL', 1, 1, 2019, '7th Edition', 'English', 1376, 'The authoritative reference on database management, relational algebra, SQL transactions, concurrency control, and distributed DBMS.', 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80', '2025-01-01 10:00:00'),
        (2, '978-1449373320', 'Designing Data-Intensive Applications', 'The Big Ideas Behind Reliable, Scalable, and Maintainable Systems', 2, 1, 2017, '1st Edition', 'English', 616, 'Explores the fundamental trade-offs in storage engines, replication, partitioning, transactions, and stream processing in distributed systems.', 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&q=80', '2025-01-01 10:00:00'),
        (3, '978-0262046305', 'Introduction to Algorithms', 'A Comprehensive Algorithmic Foundation (CLRS)', 3, 3, 2022, '4th Edition', 'English', 1312, 'The world-standard algorithms bible covering divide-and-conquer, dynamic programming, greedy algorithms, graph theory, and NP-completeness.', 'https://images.unsplash.com/photo-1532012164546-f432f2e3777a?w=400&q=80', '2025-01-01 10:00:00'),
        (4, '978-0132350884', 'Clean Code', 'A Handbook of Agile Software Craftsmanship', 4, 2, 2008, '1st Edition', 'English', 464, 'Classic software engineering guide on naming conventions, modular functions, error handling, unit testing, and refactoring techniques.', 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400&q=80', '2025-01-01 10:00:00'),
        (5, '978-1119456339', 'Operating System Concepts', 'Silberschatz Dinosaur Book', 5, 4, 2018, '10th Edition', 'English', 1230, 'Covers process synchronization, threads, CPU scheduling, virtual memory paging, deadlocks, and POSIX system call programming.', 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400&q=80', '2025-01-01 10:00:00'),
        (6, '978-0136681557', 'Computer Networking', 'A Top-Down Approach', 6, 5, 2021, '8th Edition', 'English', 864, 'Focuses on the Internet protocol stack from the application layer (HTTP, DNS) down to network routing and data link protocols.', 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&q=80', '2025-01-01 10:00:00'),
        (7, '978-0134610993', 'Artificial Intelligence: A Modern Approach', 'The Definitive AI Reference', 6, 6, 2020, '4th Edition', 'English', 1136, 'Comprehensive exploration of rational agents, search algorithms, probabilistic reasoning, deep learning architectures, and robotics.', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&q=80', '2025-01-01 10:00:00'),
        (8, '978-0321573513', 'Modern Operating Systems', 'Hardware Interaction & Kernel Implementation', 6, 4, 2014, '4th Edition', 'English', 1136, 'Andrew Tanenbaum''s lucid guide to virtualization, multicore architectures, IPC, file systems, and operating system security.', 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=400&q=80', '2025-01-01 10:00:00'),
        (9, '978-0135957059', 'The Pragmatic Programmer', 'Your Journey to Mastery', 7, 2, 2019, '20th Anniversary Edition', 'English', 352, 'Timeless principles on career development, automated tooling, orthogonal design, defensive programming, and avoiding broken windows.', 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=400&q=80', '2025-01-01 10:00:00'),
        (10, '978-0262035613', 'Deep Learning', 'Adaptive Computation and Machine Learning', 3, 6, 2016, '1st Edition', 'English', 800, 'Mathematical foundations of linear algebra, optimization, convolutional networks, sequence modeling, and representation learning.', 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400&q=80', '2025-01-01 10:00:00'),
        (11, '978-0596007126', 'Head First Design Patterns', 'Building Extensible and Maintainable Software', 2, 2, 2004, '1st Edition', 'English', 674, 'Visual and highly engaging approach to understanding Factory, Observer, Decorator, Strategy, and Singleton design patterns.', 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400&q=80', '2025-01-01 10:00:00'),
        (12, '978-0130319975', 'Database Systems: The Complete Book', 'Theory and Implementation', 6, 1, 2008, '2nd Edition', 'English', 1248, 'Detailed coverage of relational algebra, B-trees, query optimization, cost modeling, undo/redo logging, and concurrency controls.', 'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&q=80', '2025-01-01 10:00:00'),
        (13, '978-1593279288', 'Python Crash Course', 'A Hands-On, Project-Based Introduction', 8, 2, 2019, '2nd Edition', 'English', 544, 'Practical guide to Python fundamentals, object-oriented programming, data visualization, web development, and testing.', 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=400&q=80', '2025-01-01 10:00:00'),
        (14, '978-0134092669', 'Computer Systems: A Programmer''s Perspective', 'Bridging Software Execution and Hardware', 6, 4, 2015, '3rd Edition', 'English', 1120, 'Understands machine-level code representations, processor architecture, cache memories, virtual memory, and system-level I/O.', 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=400&q=80', '2025-01-01 10:00:00'),
        (15, '978-0262510875', 'Structure and Interpretation of Computer Programs', 'SICP: Conceptual Computing Architecture', 3, 2, 1996, '2nd Edition', 'English', 657, 'The MIT classic on computational processes, higher-order abstractions, metalinguistic abstraction, and register machines.', 'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=400&q=80', '2025-01-01 10:00:00'),
        (16, '978-0321125217', 'Domain-Driven Design', 'Tackling Complexity in the Heart of Software', 7, 2, 2003, '1st Edition', 'English', 560, 'Eric Evans'' seminal work on ubiquitous language, bounded contexts, entities, value objects, aggregates, and repositories.', 'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=400&q=80', '2025-01-01 10:00:00')
    ]
    cur.executemany("INSERT INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", books)

    # 6. Book Authors
    book_authors = [
        (1, 1), (1, 2), (1, 3),
        (2, 4),
        (3, 5), (3, 6), (3, 7), (3, 8),
        (4, 9),
        (5, 1), (5, 10),
        (6, 11), (6, 12),
        (7, 13), (7, 14),
        (8, 15),
        (9, 16), (9, 17),
        (10, 18),
        (11, 4),
        (12, 1), (12, 2),
        (13, 16),
        (14, 15),
        (15, 5),
        (16, 9)
    ]
    cur.executemany("INSERT INTO book_authors VALUES (?,?)", book_authors)

    # 7. Book Copies
    copies = [
        (1, 1, 'BC-1001', 'Aisle 1, Shelf A-1', 'new', 'available'),
        (2, 1, 'BC-1002', 'Aisle 1, Shelf A-1', 'good', 'issued'),
        (3, 1, 'BC-1003', 'Aisle 1, Shelf A-2', 'good', 'reserved'),
        (4, 2, 'BC-1004', 'Aisle 1, Shelf B-1', 'new', 'available'),
        (5, 2, 'BC-1005', 'Aisle 1, Shelf B-1', 'good', 'available'),
        (6, 2, 'BC-1006', 'Aisle 1, Shelf B-2', 'good', 'issued'),
        (7, 3, 'BC-1007', 'Aisle 2, Shelf A-1', 'new', 'available'),
        (8, 3, 'BC-1008', 'Aisle 2, Shelf A-1', 'good', 'issued'),
        (9, 3, 'BC-1009', 'Aisle 2, Shelf A-2', 'damaged', 'available'),
        (10, 4, 'BC-1010', 'Aisle 2, Shelf B-1', 'good', 'available'),
        (11, 4, 'BC-1011', 'Aisle 2, Shelf B-1', 'new', 'available'),
        (12, 5, 'BC-1012', 'Aisle 3, Shelf A-1', 'good', 'available'),
        (13, 5, 'BC-1013', 'Aisle 3, Shelf A-2', 'good', 'issued'),
        (14, 6, 'BC-1014', 'Aisle 3, Shelf B-1', 'new', 'available'),
        (15, 6, 'BC-1015', 'Aisle 3, Shelf B-2', 'good', 'available'),
        (16, 7, 'BC-1016', 'Aisle 4, Shelf A-1', 'new', 'available'),
        (17, 7, 'BC-1017', 'Aisle 4, Shelf A-2', 'good', 'issued'),
        (18, 8, 'BC-1018', 'Aisle 4, Shelf B-1', 'good', 'available'),
        (19, 8, 'BC-1019', 'Aisle 4, Shelf B-2', 'good', 'available'),
        (20, 9, 'BC-1020', 'Aisle 5, Shelf A-1', 'new', 'available'),
        (21, 9, 'BC-1021', 'Aisle 5, Shelf A-2', 'good', 'available'),
        (22, 10, 'BC-1022', 'Aisle 5, Shelf B-1', 'new', 'available'),
        (23, 10, 'BC-1023', 'Aisle 5, Shelf B-2', 'good', 'available'),
        (24, 11, 'BC-1024', 'Aisle 6, Shelf A-1', 'good', 'available'),
        (25, 11, 'BC-1025', 'Aisle 6, Shelf A-2', 'good', 'available'),
        (26, 12, 'BC-1026', 'Aisle 1, Shelf C-1', 'good', 'available'),
        (27, 12, 'BC-1027', 'Aisle 1, Shelf C-2', 'damaged', 'available'),
        (28, 13, 'BC-1028', 'Aisle 6, Shelf B-1', 'new', 'available'),
        (29, 13, 'BC-1029', 'Aisle 6, Shelf B-2', 'good', 'available'),
        (30, 14, 'BC-1030', 'Aisle 3, Shelf C-1', 'new', 'available'),
        (31, 14, 'BC-1031', 'Aisle 3, Shelf C-2', 'good', 'available'),
        (32, 15, 'BC-1032', 'Aisle 2, Shelf C-1', 'good', 'available'),
        (33, 15, 'BC-1033', 'Aisle 2, Shelf C-2', 'good', 'available'),
        (34, 16, 'BC-1034', 'Aisle 5, Shelf C-1', 'new', 'available'),
        (35, 16, 'BC-1035', 'Aisle 5, Shelf C-2', 'good', 'available'),
        (36, 1,  'BC-1036', 'Aisle 1, Shelf A-3', 'new', 'issued')
    ]
    cur.executemany("INSERT INTO book_copies VALUES (?,?,?,?,?,?)", copies)

    # 8. Loans
    loans = [
        (1, 2, 2, 1, '2026-11-01 10:00:00', '2026-11-20 23:59:59', None, 'active'),
        (2, 6, 3, 1, '2026-10-15 11:30:00', '2026-11-05 23:59:59', None, 'overdue'),
        (3, 8, 4, 1, '2026-10-10 14:15:00', '2026-11-01 23:59:59', None, 'overdue'),
        (4, 13, 5, 1, '2026-11-08 09:45:00', '2026-11-22 23:59:59', None, 'active'),
        (5, 17, 6, 1, '2026-11-10 16:00:00', '2026-11-24 23:59:59', None, 'active'),
        (6, 36, 2, 1, '2026-11-05 13:20:00', '2026-11-19 23:59:59', None, 'active'),
        (7, 4, 2, 1, '2026-09-01 10:00:00', '2026-09-15 23:59:59', '2026-09-14 15:30:00', 'returned'),
        (8, 7, 3, 1, '2026-09-05 11:00:00', '2026-09-19 23:59:59', '2026-09-24 16:00:00', 'returned'),
        (9, 10, 4, 1, '2026-09-10 14:00:00', '2026-09-24 23:59:59', '2026-09-29 17:00:00', 'returned'),
        (10, 14, 6, 1, '2026-09-15 12:00:00', '2026-09-29 23:59:59', '2026-10-04 14:30:00', 'returned')
    ]
    cur.executemany("INSERT INTO loans VALUES (?,?,?,?,?,?,?,?)", loans)

    # 9. Fines
    fines = [
        (1, 8, 3, 5.0, 'unpaid', None),
        (2, 9, 4, 5.0, 'paid', '2026-09-30 11:20:00'),
        (3, 10, 6, 5.0, 'waived', None)
    ]
    cur.executemany("INSERT INTO fines VALUES (?,?,?,?,?,?)", fines)

    # 10. Waitlist
    waitlist_items = [
        (1, 1, 3, '2026-11-02 10:15:00', 'waiting'),
        (2, 1, 4, '2026-11-03 14:20:00', 'waiting'),
        (3, 1, 6, '2026-10-28 09:00:00', 'notified'),
        (4, 2, 5, '2026-11-06 16:45:00', 'waiting')
    ]
    cur.executemany("INSERT INTO waitlist VALUES (?,?,?,?,?)", waitlist_items)

    # 11. Study Rooms & Bookings
    rooms = [
        (1, 'Turing Collaborative Lab (Room 101)', 6, 1, 1),
        (2, 'Lovelace Quiet Study (Room 102)', 2, 0, 1),
        (3, 'Knuth Group Discussion (Room 201)', 8, 1, 1),
        (4, 'Dijkstra Seminar Pod (Room 202)', 4, 1, 1)
    ]
    cur.executemany("INSERT INTO study_rooms VALUES (?,?,?,?,?)", rooms)

    today_str = datetime.now().strftime("%Y-%m-%d")
    bookings = [
        (1, 1, 2, today_str, '09:00:00', '11:00:00', 'confirmed'),
        (2, 1, 3, today_str, '13:00:00', '15:00:00', 'confirmed'),
        (3, 2, 4, today_str, '10:00:00', '12:00:00', 'confirmed'),
        (4, 3, 5, today_str, '14:00:00', '16:00:00', 'confirmed')
    ]
    cur.executemany("INSERT INTO room_bookings VALUES (?,?,?,?,?,?,?)", bookings)

    # 12. Book Requests & Votes
    requests = [
        (1, 'Building Microservices: Designing Fine-Grained Systems', 'Sam Newman', '978-1492034025', 2, 49.99, 'open', '2026-11-01 10:00:00'),
        (2, 'Site Reliability Engineering: How Google Runs Production Systems', 'Niall Richard Murphy et al.', '978-1491929124', 3, 44.50, 'approved', '2026-11-02 11:30:00'),
        (3, 'Rust Programming Language', 'Steve Klabnik and Carol Nichols', '978-1718503106', 4, 39.95, 'purchased', '2026-10-20 15:00:00')
    ]
    cur.executemany("INSERT INTO book_requests VALUES (?,?,?,?,?,?,?,?)", requests)

    votes = [
        (1, 2, '2026-11-01 10:01:00'),
        (1, 3, '2026-11-01 12:45:00'),
        (1, 4, '2026-11-02 09:10:00'),
        (1, 5, '2026-11-03 14:00:00'),
        (2, 3, '2026-11-02 11:31:00'),
        (2, 4, '2026-11-02 16:20:00'),
        (2, 6, '2026-11-03 11:00:00'),
        (3, 4, '2026-10-20 15:05:00'),
        (3, 2, '2026-10-21 08:30:00')
    ]
    cur.executemany("INSERT INTO request_votes VALUES (?,?,?)", votes)

    # 13. Audit Logs
    audit_logs = [
        (1, 1, 'FINE_WAIVED', 'fines', 3, '{"amount": 5.0, "status": "unpaid"}', '{"amount": 5.0, "status": "waived"}', '2026-10-05 14:35:00'),
        (2, 1, 'BOOK_DELETED', 'books', 99, '{"title": "Deprecated Legacy Fortran 77", "isbn": "978-0000000001"}', None, '2026-10-12 09:15:00'),
        (3, 1, 'COPY_STATUS_CHANGE', 'book_copies', 3, '{"barcode": "BC-1003", "status": "available"}', '{"barcode": "BC-1003", "status": "reserved"}', '2026-10-28 09:01:00')
    ]
    cur.executemany("INSERT INTO audit_logs VALUES (?,?,?,?,?,?,?,?)", audit_logs)

    conn.commit()
    print("[*] SQLite database populated successfully!")

def _run_mysql_scripts():
    """Runs schema.sql and seed.sql on the MySQL connection."""
    schema_path = os.path.join(PROJECT_ROOT, "schema.sql")
    seed_path = os.path.join(PROJECT_ROOT, "seed.sql")
    
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        autocommit=True
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4;")
            cur.execute(f"USE {MYSQL_DATABASE};")
            
            # Read schema file and split statements
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                # Execute non-delimiter statements
                for stmt in re.split(r";\s*$", schema_sql, flags=re.MULTILINE):
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith("DELIMITER"):
                        cur.execute(stmt)
                        
            if os.path.exists(seed_path):
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_sql = f.read()
                for stmt in re.split(r";\s*$", seed_sql, flags=re.MULTILINE):
                    stmt = stmt.strip()
                    if stmt:
                        cur.execute(stmt)
        print("[*] MySQL database schema and seed initialized successfully!")
    finally:
        conn.close()
