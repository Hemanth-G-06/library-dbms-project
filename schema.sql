-- ============================================================================
-- SMART LIBRARY MANAGEMENT SYSTEM (DBMS PROJECT)
-- Database DDL Schema (Normalized 3NF + Triggers, Views, Foreign Keys, Indexes)
-- Target DBMS: MySQL 8.0+ / MariaDB 10.5+
-- ============================================================================

-- Create Database if not exists and switch context
CREATE DATABASE IF NOT EXISTS smart_library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_library_db;

-- Disable foreign key checks for clean teardown/rebuild
SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS v_active_loans_summary;
DROP VIEW IF EXISTS v_overdue_fines;
DROP VIEW IF EXISTS v_catalog_availability;

DROP TRIGGER IF EXISTS trg_loan_return_waitlist;
DROP TRIGGER IF EXISTS trg_loan_fine_calculation;
DROP TRIGGER IF EXISTS trg_fine_waived_audit;
DROP TRIGGER IF EXISTS trg_book_delete_audit;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS request_votes;
DROP TABLE IF EXISTS book_requests;
DROP TABLE IF EXISTS room_bookings;
DROP TABLE IF EXISTS study_rooms;
DROP TABLE IF EXISTS waitlist;
DROP TABLE IF EXISTS fines;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS book_copies;
DROP TABLE IF EXISTS book_authors;
DROP TABLE IF EXISTS authors;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS publishers;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. USERS TABLE
-- Stores credentials, role ('admin' vs 'member'), and membership status
-- ============================================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    library_card_no VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NULL,
    role ENUM('admin', 'member') NOT NULL DEFAULT 'member',
    status ENUM('active', 'suspended') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_card (library_card_no),
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- ============================================================================
-- 2. CATEGORIES TABLE
-- Stores standardized book categories / genres (Normalized)
-- ============================================================================
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL UNIQUE,
    description TEXT NULL
) ENGINE=InnoDB;

-- ============================================================================
-- 3. PUBLISHERS TABLE
-- Stores publication houses (Normalized)
-- ============================================================================
CREATE TABLE publishers (
    publisher_id INT AUTO_INCREMENT PRIMARY KEY,
    publisher_name VARCHAR(150) NOT NULL UNIQUE,
    country VARCHAR(80) NULL,
    website VARCHAR(200) NULL
) ENGINE=InnoDB;

-- ============================================================================
-- 4. BOOKS TABLE (Abstract Catalog Titles)
-- Normalized to 3NF: depends strictly on book_id
-- ============================================================================
CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255) NULL,
    publisher_id INT NULL,
    category_id INT NOT NULL,
    publication_year INT NULL,
    edition VARCHAR(50) NULL,
    language VARCHAR(50) NOT NULL DEFAULT 'English',
    pages INT NULL,
    description TEXT NULL,
    cover_image_url VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_books_publisher FOREIGN KEY (publisher_id)
        REFERENCES publishers(publisher_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_books_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_books_pages CHECK (pages IS NULL OR pages > 0),
    INDEX idx_books_isbn (isbn),
    INDEX idx_books_title (title),
    INDEX idx_books_category (category_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 5. AUTHORS TABLE
-- Authors normalized separately from books to support Many-to-Many
-- ============================================================================
CREATE TABLE authors (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    bio TEXT NULL,
    INDEX idx_authors_name (name)
) ENGINE=InnoDB;

-- ============================================================================
-- 6. BOOK_AUTHORS (M:N Bridge Table)
-- Resolves Many-to-Many between Books and Authors (Composite Primary Key)
-- ============================================================================
CREATE TABLE book_authors (
    book_id INT NOT NULL,
    author_id INT NOT NULL,
    PRIMARY KEY (book_id, author_id),
    CONSTRAINT fk_ba_book FOREIGN KEY (book_id)
        REFERENCES books(book_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ba_author FOREIGN KEY (author_id)
        REFERENCES authors(author_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 7. BOOK_COPIES (Physical Inventory Tracking)
-- Tracks each physical instance of a book with its barcode and shelf location
-- ============================================================================
CREATE TABLE book_copies (
    copy_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    barcode VARCHAR(50) NOT NULL UNIQUE,
    shelf_location VARCHAR(80) NOT NULL,
    `condition` ENUM('new', 'good', 'damaged') NOT NULL DEFAULT 'good',
    status ENUM('available', 'issued', 'reserved', 'lost') NOT NULL DEFAULT 'available',
    CONSTRAINT fk_copies_book FOREIGN KEY (book_id)
        REFERENCES books(book_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_copies_barcode (barcode),
    INDEX idx_copies_status (status),
    INDEX idx_copies_book_status (book_id, status)
) ENGINE=InnoDB;

-- ============================================================================
-- 8. LOANS (Borrowing Transactions)
-- Atomic borrowing records with issue, due, and return timestamps
-- ============================================================================
CREATE TABLE loans (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    copy_id INT NOT NULL,
    user_id INT NOT NULL,
    issued_by INT NOT NULL,
    issue_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME NOT NULL,
    return_date DATETIME NULL,
    status ENUM('active', 'returned', 'overdue') NOT NULL DEFAULT 'active',
    CONSTRAINT fk_loans_copy FOREIGN KEY (copy_id)
        REFERENCES book_copies(copy_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_loans_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_loans_issuer FOREIGN KEY (issued_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_loans_user (user_id),
    INDEX idx_loans_copy (copy_id),
    INDEX idx_loans_status (status),
    INDEX idx_loans_due_date (due_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 9. FINES
-- Calculates and manages overdue fines ($1.00 per overdue day)
-- ============================================================================
CREATE TABLE fines (
    fine_id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL UNIQUE,
    user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_status ENUM('unpaid', 'paid', 'waived') NOT NULL DEFAULT 'unpaid',
    paid_date DATETIME NULL,
    CONSTRAINT fk_fines_loan FOREIGN KEY (loan_id)
        REFERENCES loans(loan_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_fines_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_fines_amount CHECK (amount >= 0.00),
    INDEX idx_fines_user (user_id),
    INDEX idx_fines_status (payment_status)
) ENGINE=InnoDB;

-- ============================================================================
-- 10. WAITLIST (FIFO Reservation Queue)
-- Tracks users waiting for popular books when 0 copies are available
-- ============================================================================
CREATE TABLE waitlist (
    waitlist_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    user_id INT NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('waiting', 'notified', 'expired', 'fulfilled') NOT NULL DEFAULT 'waiting',
    CONSTRAINT fk_waitlist_book FOREIGN KEY (book_id)
        REFERENCES books(book_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_waitlist_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_waitlist_book_time (book_id, requested_at),
    INDEX idx_waitlist_user (user_id),
    INDEX idx_waitlist_status (status)
) ENGINE=InnoDB;

-- ============================================================================
-- 11. STUDY_ROOMS & ROOM_BOOKINGS (Conflict-Free Slot Booking)
-- ============================================================================
CREATE TABLE study_rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_name VARCHAR(80) NOT NULL UNIQUE,
    capacity INT NOT NULL DEFAULT 4,
    has_whiteboard BOOLEAN NOT NULL DEFAULT TRUE,
    has_power_outlets BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_room_capacity CHECK (capacity > 0)
) ENGINE=InnoDB;

CREATE TABLE room_bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status ENUM('confirmed', 'cancelled') NOT NULL DEFAULT 'confirmed',
    CONSTRAINT fk_bookings_room FOREIGN KEY (room_id)
        REFERENCES study_rooms(room_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_bookings_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_booking_time CHECK (start_time < end_time),
    INDEX idx_bookings_date_room (booking_date, room_id, status)
) ENGINE=InnoDB;

-- ============================================================================
-- 12. BOOK_REQUESTS & REQUEST_VOTES (Crowdsourced Acquisition Voting)
-- ============================================================================
CREATE TABLE book_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(150) NOT NULL,
    isbn VARCHAR(20) NULL,
    requested_by INT NOT NULL,
    estimated_price DECIMAL(10,2) NULL,
    status ENUM('open', 'approved', 'purchased') NOT NULL DEFAULT 'open',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_breq_user FOREIGN KEY (requested_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_breq_status (status)
) ENGINE=InnoDB;

CREATE TABLE request_votes (
    request_id INT NOT NULL,
    user_id INT NOT NULL,
    voted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id, user_id),
    CONSTRAINT fk_rv_request FOREIGN KEY (request_id)
        REFERENCES book_requests(request_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_rv_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 13. AUDIT_LOGS (Tamper-Proof Accountability)
-- Automatically populated by DB triggers on administrative actions
-- ============================================================================
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    actor_id INT NULL,
    action_type VARCHAR(50) NOT NULL,
    target_table VARCHAR(50) NOT NULL,
    target_record_id INT NOT NULL,
    old_value JSON NULL,
    new_value JSON NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_audit_table (target_table),
    INDEX idx_audit_time (timestamp)
) ENGINE=InnoDB;

-- ============================================================================
-- SQL TRIGGERS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TRIGGER 1: Automated FIFO Waitlist Processor
-- Fired AFTER loans UPDATE when return_date is populated.
-- Checks the waitlist for the oldest waiting student. If found, reserves the
-- copy for them and marks their waitlist status as 'notified'.
-- Otherwise, returns the physical copy to 'available' status.
-- ----------------------------------------------------------------------------
DELIMITER //
CREATE TRIGGER trg_loan_return_waitlist
AFTER UPDATE ON loans
FOR EACH ROW
BEGIN
    DECLARE v_book_id INT;
    DECLARE v_oldest_waitlist_id INT DEFAULT NULL;
    DECLARE v_waiting_user_id INT DEFAULT NULL;

    -- Only proceed when book is actually returned
    IF NEW.return_date IS NOT NULL AND OLD.return_date IS NULL THEN
        -- Get the book_id associated with this copy
        SELECT book_id INTO v_book_id 
        FROM book_copies 
        WHERE copy_id = NEW.copy_id;

        -- Find the oldest waiting patron (FIFO)
        SELECT waitlist_id, user_id INTO v_oldest_waitlist_id, v_waiting_user_id
        FROM waitlist
        WHERE book_id = v_book_id AND status = 'waiting'
        ORDER BY requested_at ASC
        LIMIT 1;

        IF v_oldest_waitlist_id IS NOT NULL THEN
            -- Reserve the copy for the top queued member
            UPDATE book_copies 
            SET status = 'reserved' 
            WHERE copy_id = NEW.copy_id;

            -- Update queue item to notified
            UPDATE waitlist 
            SET status = 'notified' 
            WHERE waitlist_id = v_oldest_waitlist_id;
        ELSE
            -- No active waitlist entry, copy returns to circulation
            UPDATE book_copies 
            SET status = 'available' 
            WHERE copy_id = NEW.copy_id;
        END IF;
    END IF;
END //
DELIMITER ;

-- ----------------------------------------------------------------------------
-- TRIGGER 2: Automated Fine Generation
-- Fired AFTER loans UPDATE when return_date is populated.
-- If the return_date > due_date, automatically generates a calculated fine
-- based on days overdue ($1.00 per overdue day) in the fines table.
-- ----------------------------------------------------------------------------
DELIMITER //
CREATE TRIGGER trg_loan_fine_calculation
AFTER UPDATE ON loans
FOR EACH ROW
BEGIN
    DECLARE v_days_overdue INT DEFAULT 0;
    DECLARE v_fine_rate DECIMAL(10,2) DEFAULT 1.00;

    IF NEW.return_date IS NOT NULL AND OLD.return_date IS NULL THEN
        IF NEW.return_date > NEW.due_date THEN
            SET v_days_overdue = DATEDIFF(NEW.return_date, NEW.due_date);
            IF v_days_overdue > 0 THEN
                INSERT INTO fines (loan_id, user_id, amount, payment_status, paid_date)
                VALUES (NEW.loan_id, NEW.user_id, v_days_overdue * v_fine_rate, 'unpaid', NULL);
            END IF;
        END IF;
    END IF;
END //
DELIMITER ;

-- ----------------------------------------------------------------------------
-- TRIGGER 3A: Audit Logging for Waived Fines
-- Fired AFTER fines UPDATE when payment_status is set to 'waived'.
-- Logs the action to audit_logs with JSON formatted old & new records.
-- ----------------------------------------------------------------------------
DELIMITER //
CREATE TRIGGER trg_fine_waived_audit
AFTER UPDATE ON fines
FOR EACH ROW
BEGIN
    IF NEW.payment_status = 'waived' AND OLD.payment_status != 'waived' THEN
        INSERT INTO audit_logs (actor_id, action_type, target_table, target_record_id, old_value, new_value, timestamp)
        VALUES (
            NEW.user_id,
            'FINE_WAIVED',
            'fines',
            NEW.fine_id,
            JSON_OBJECT('amount', OLD.amount, 'status', OLD.payment_status),
            JSON_OBJECT('amount', NEW.amount, 'status', NEW.payment_status),
            NOW()
        );
    END IF;
END //
DELIMITER ;

-- ----------------------------------------------------------------------------
-- TRIGGER 3B: Audit Logging for Book Deletions
-- Fired AFTER books DELETE. Records the catalog deletion in audit_logs.
-- ----------------------------------------------------------------------------
DELIMITER //
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
        JSON_OBJECT('title', OLD.title, 'isbn', OLD.isbn),
        NULL,
        NOW()
    );
END //
DELIMITER ;

-- ============================================================================
-- SQL VIEWS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VIEW: v_catalog_availability
-- Aggregates book titles, authors, categories, publishers, and counts physical
-- copies categorized by status ('available', 'issued', 'reserved') without
-- Cartesian fan-out from multiple authors.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_catalog_availability AS
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
        GROUP_CONCAT(DISTINCT a.name ORDER BY a.name SEPARATOR ', ') AS authors,
        GROUP_CONCAT(DISTINCT a.author_id ORDER BY a.author_id SEPARATOR ', ') AS author_ids
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

-- ----------------------------------------------------------------------------
-- VIEW: v_active_loans_summary
-- Convenient query view for active loans with user, book copy, and due status.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_loans_summary AS
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
        WHEN l.return_date IS NULL AND NOW() > l.due_date THEN 'OVERDUE'
        WHEN l.return_date IS NULL THEN 'ON_LOAN'
        ELSE 'RETURNED'
    END AS display_status,
    GREATEST(0, DATEDIFF(COALESCE(l.return_date, NOW()), l.due_date)) AS days_overdue
FROM loans l
JOIN users u ON l.user_id = u.user_id
JOIN book_copies bc ON l.copy_id = bc.copy_id
JOIN books b ON bc.book_id = b.book_id;
