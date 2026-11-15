-- ============================================================================
-- SMART LIBRARY MANAGEMENT SYSTEM (DBMS PROJECT)
-- Realistic Seed Dataset (Users, Categories, Publishers, Books, Authors,
-- Copies, Loans, Overdue Fines, Waitlists, Study Rooms, Book Requests, Audit Logs)
-- ============================================================================

USE smart_library_db;

-- Clear previous data in correct dependency order
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE request_votes;
TRUNCATE TABLE book_requests;
TRUNCATE TABLE room_bookings;
TRUNCATE TABLE study_rooms;
TRUNCATE TABLE waitlist;
TRUNCATE TABLE fines;
TRUNCATE TABLE loans;
TRUNCATE TABLE book_copies;
TRUNCATE TABLE book_authors;
TRUNCATE TABLE authors;
TRUNCATE TABLE books;
TRUNCATE TABLE publishers;
TRUNCATE TABLE categories;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. SEED USERS (1 Admin + 5 Students)
-- Passwords:
-- Admin: 'adminpassword123'
-- Students: 'studentpassword123'
-- ============================================================================
INSERT INTO users (user_id, library_card_no, full_name, email, password_hash, phone, role, status, created_at) VALUES
(1, 'LIB-ADM-001', 'Dr. Eleanor Vance', 'admin@library.edu', '$2b$12$OyGweI82sDmXEf9b7I2gleB5c9pk2jVReYXnoerdmQy2.wDi3tYq2', '+1-555-0100', 'admin', 'active', '2025-01-01 08:00:00'),
(2, 'LIB-STU-101', 'Alex Rivera', 'alex.rivera@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0101', 'member', 'active', '2025-01-10 09:30:00'),
(3, 'LIB-STU-102', 'Sarah Chen', 'sarah.chen@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0102', 'member', 'active', '2025-01-12 11:15:00'),
(4, 'LIB-STU-103', 'Michael Adebayo', 'michael.adebayo@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0103', 'member', 'active', '2025-01-15 14:00:00'),
(5, 'LIB-STU-104', 'Priya Sharma', 'priya.sharma@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0104', 'member', 'active', '2025-01-18 10:45:00'),
(6, 'LIB-STU-105', 'David Kim', 'david.kim@student.edu', '$2b$12$f8VC6o7rlF70kuAalhTeXuO0hyeJiIFlMiiLKWJPbmSj.1kmXt/42', '+1-555-0105', 'member', 'active', '2025-01-20 16:20:00');

-- ============================================================================
-- 2. SEED CATEGORIES
-- ============================================================================
INSERT INTO categories (category_id, category_name, description) VALUES
(1, 'Database Systems', 'Relational design, normalization, SQL, indexing, distributed databases, and transaction processing.'),
(2, 'Software Engineering', 'System architecture, design patterns, clean code, agile methodologies, and testing.'),
(3, 'Algorithms & Data Structures', 'Algorithmic paradigms, complexity analysis, graph algorithms, and data representation.'),
(4, 'Operating Systems', 'Kernel architecture, memory virtualization, concurrency, file systems, and scheduling.'),
(5, 'Computer Networks', 'Protocol layers, TCP/IP, network security, routing, and cloud infrastructure.'),
(6, 'Artificial Intelligence', 'Machine learning, neural networks, natural language processing, and heuristics.');

-- ============================================================================
-- 3. SEED PUBLISHERS
-- ============================================================================
INSERT INTO publishers (publisher_id, publisher_name, country, website) VALUES
(1, 'McGraw-Hill Education', 'United States', 'https://www.mheducation.com'),
(2, 'O''Reilly Media', 'United States', 'https://www.oreilly.com'),
(3, 'MIT Press', 'United States', 'https://mitpress.mit.edu'),
(4, 'Prentice Hall', 'United States', 'https://www.pearson.com'),
(5, 'John Wiley & Sons', 'United States', 'https://www.wiley.com'),
(6, 'Pearson Education', 'United Kingdom', 'https://www.pearson.com'),
(7, 'Addison-Wesley Professional', 'United States', 'https://www.informit.com'),
(8, 'No Starch Press', 'United States', 'https://nostarch.com');

-- ============================================================================
-- 4. SEED AUTHORS
-- ============================================================================
INSERT INTO authors (author_id, name, bio) VALUES
(1, 'Abraham Silberschatz', 'Professor of Computer Science at Yale University specializing in database systems and operating systems.'),
(2, 'Henry F. Korth', 'Professor of Computer Science and Engineering at Lehigh University.'),
(3, 'S. Sudarshan', 'Professor of Computer Science and Engineering at IIT Bombay.'),
(4, 'Martin Kleppmann', 'Associate Professor in Distributed Systems at the University of Cambridge and author on data systems.'),
(5, 'Thomas H. Cormen', 'Professor of Computer Science at Dartmouth College and co-author of CLRS.'),
(6, 'Charles E. Leiserson', 'Professor of Computer Science and Engineering at MIT.'),
(7, 'Ronald L. Rivest', 'Professor of Computer Science at MIT and co-inventor of the RSA cryptosystem.'),
(8, 'Clifford Stein', 'Professor of Industrial Engineering and Operations Research at Columbia University.'),
(9, 'Robert C. Martin', 'Renowned software engineer widely known as "Uncle Bob", pioneer of Agile manifesto and SOLID principles.'),
(10, 'Peter B. Galvin', 'Chief Technologist at Corporate Technologies and co-author of Operating System Concepts.'),
(11, 'James F. Kurose', 'Distinguished Professor Emeritus in the College of Information and Computer Sciences at UMass Amherst.'),
(12, 'Keith W. Ross', 'Professor of Computer Science and Engineering at NYU Tandon School of Engineering.'),
(13, 'Stuart Russell', 'Professor of Computer Science at UC Berkeley and leading researcher in artificial intelligence.'),
(14, 'Peter Norvig', 'Director of Research at Google and co-author of the seminal AI textbook.'),
(15, 'Andrew S. Tanenbaum', 'Emeritus Professor at Vrije Universiteit Amsterdam and creator of the MINIX operating system.'),
(16, 'David Thomas', 'One of the original authors of The Pragmatic Programmer and Agile Manifesto.'),
(17, 'Andrew Hunt', 'Co-author of The Pragmatic Programmer and founder of the Pragmatic Bookshelf.'),
(18, 'Ian Goodfellow', 'Research scientist specializing in deep generative models and GANs.');

-- ============================================================================
-- 5. SEED BOOKS (16 Distinct Catalog Titles)
-- ============================================================================
INSERT INTO books (book_id, isbn, title, subtitle, publisher_id, category_id, publication_year, edition, language, pages, description, cover_image_url) VALUES
(1, '978-0078022159', 'Database System Concepts', 'Complete Fundamentals of Relational Systems & SQL', 1, 1, 2019, '7th Edition', 'English', 1376, 'The authoritative reference on database management, relational algebra, SQL transactions, concurrency control, and distributed DBMS.', 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80'),
(2, '978-1449373320', 'Designing Data-Intensive Applications', 'The Big Ideas Behind Reliable, Scalable, and Maintainable Systems', 2, 1, 2017, '1st Edition', 'English', 616, 'Explores the fundamental trade-offs in storage engines, replication, partitioning, transactions, and stream processing in distributed systems.', 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&q=80'),
(3, '978-0262046305', 'Introduction to Algorithms', 'A Comprehensive Algorithmic Foundation (CLRS)', 3, 3, 2022, '4th Edition', 'English', 1312, 'The world-standard algorithms bible covering divide-and-conquer, dynamic programming, greedy algorithms, graph theory, and NP-completeness.', 'https://images.unsplash.com/photo-1532012164546-f432f2e3777a?w=400&q=80'),
(4, '978-0132350884', 'Clean Code', 'A Handbook of Agile Software Craftsmanship', 4, 2, 2008, '1st Edition', 'English', 464, 'Classic software engineering guide on naming conventions, modular functions, error handling, unit testing, and refactoring techniques.', 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400&q=80'),
(5, '978-1119456339', 'Operating System Concepts', 'Silberschatz Dinosaur Book', 5, 4, 2018, '10th Edition', 'English', 1230, 'Covers process synchronization, threads, CPU scheduling, virtual memory paging, deadlocks, and POSIX system call programming.', 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400&q=80'),
(6, '978-0136681557', 'Computer Networking', 'A Top-Down Approach', 6, 5, 2021, '8th Edition', 'English', 864, 'Focuses on the Internet protocol stack from the application layer (HTTP, DNS) down to network routing and data link protocols.', 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&q=80'),
(7, '978-0134610993', 'Artificial Intelligence: A Modern Approach', 'The Definitive AI Reference', 6, 6, 2020, '4th Edition', 'English', 1136, 'Comprehensive exploration of rational agents, search algorithms, probabilistic reasoning, deep learning architectures, and robotics.', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&q=80'),
(8, '978-0321573513', 'Modern Operating Systems', 'Hardware Interaction & Kernel Implementation', 6, 4, 2014, '4th Edition', 'English', 1136, 'Andrew Tanenbaum''s lucid guide to virtualization, multicore architectures, IPC, file systems, and operating system security.', 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=400&q=80'),
(9, '978-0135957059', 'The Pragmatic Programmer', 'Your Journey to Mastery', 7, 2, 2019, '20th Anniversary Edition', 'English', 352, 'Timeless principles on career development, automated tooling, orthogonal design, defensive programming, and avoiding broken windows.', 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=400&q=80'),
(10, '978-0262035613', 'Deep Learning', 'Adaptive Computation and Machine Learning', 3, 6, 2016, '1st Edition', 'English', 800, 'Mathematical foundations of linear algebra, optimization, convolutional networks, sequence modeling, and representation learning.', 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400&q=80'),
(11, '978-0596007126', 'Head First Design Patterns', 'Building Extensible and Maintainable Software', 2, 2, 2004, '1st Edition', 'English', 674, 'Visual and highly engaging approach to understanding Factory, Observer, Decorator, Strategy, and Singleton design patterns.', 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400&q=80'),
(12, '978-0130319975', 'Database Systems: The Complete Book', 'Theory and Implementation', 6, 1, 2008, '2nd Edition', 'English', 1248, 'Detailed coverage of relational algebra, B-trees, query optimization, cost modeling, undo/redo logging, and concurrency controls.', 'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&q=80'),
(13, '978-1593279288', 'Python Crash Course', 'A Hands-On, Project-Based Introduction', 8, 2, 2019, '2nd Edition', 'English', 544, 'Practical guide to Python fundamentals, object-oriented programming, data visualization, web development, and testing.', 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=400&q=80'),
(14, '978-0134092669', 'Computer Systems: A Programmer''s Perspective', 'Bridging Software Execution and Hardware', 6, 4, 2015, '3rd Edition', 'English', 1120, 'Understands machine-level code representations, processor architecture, cache memories, virtual memory, and system-level I/O.', 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=400&q=80'),
(15, '978-0262510875', 'Structure and Interpretation of Computer Programs', 'SICP: Conceptual Computing Architecture', 3, 2, 1996, '2nd Edition', 'English', 657, 'The MIT classic on computational processes, higher-order abstractions, metalinguistic abstraction, and register machines.', 'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=400&q=80'),
(16, '978-0321125217', 'Domain-Driven Design', 'Tackling Complexity in the Heart of Software', 7, 2, 2003, '1st Edition', 'English', 560, 'Eric Evans'' seminal work on ubiquitous language, bounded contexts, entities, value objects, aggregates, and repositories.', 'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=400&q=80');

-- ============================================================================
-- 6. SEED BOOK_AUTHORS (Bridge Table for M:N Relationships)
-- ============================================================================
INSERT INTO book_authors (book_id, author_id) VALUES
(1, 1), (1, 2), (1, 3),   -- Silberschatz, Korth, Sudarshan
(2, 4),                   -- Kleppmann
(3, 5), (3, 6), (3, 7), (3, 8), -- Cormen, Leiserson, Rivest, Stein
(4, 9),                   -- Martin
(5, 1), (5, 10),          -- Silberschatz, Galvin
(6, 11), (6, 12),         -- Kurose, Ross
(7, 13), (7, 14),         -- Russell, Norvig
(8, 15),                  -- Tanenbaum
(9, 16), (9, 17),         -- Thomas, Hunt
(10, 18),                 -- Goodfellow
(11, 4),                  -- Kleppmann / Editorial
(12, 1), (12, 2),         -- Silberschatz, Korth
(13, 16),                 -- Thomas
(14, 15),                 -- Tanenbaum
(15, 5),                  -- Cormen
(16, 9);                  -- Martin

-- ============================================================================
-- 7. SEED BOOK_COPIES (36 Physical Copies Across Shelves)
-- ============================================================================
INSERT INTO book_copies (copy_id, book_id, barcode, shelf_location, `condition`, status) VALUES
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
(36, 1,  'BC-1036', 'Aisle 1, Shelf A-3', 'new', 'issued');

-- ============================================================================
-- 8. SEED LOANS (Active, Overdue, and Returned Loans)
-- ============================================================================
INSERT INTO loans (loan_id, copy_id, user_id, issued_by, issue_date, due_date, return_date, status) VALUES
-- Loan 1: Alex Rivera borrowed Database System Concepts (Active, Due Soon)
(1, 2, 2, 1, '2026-11-01 10:00:00', '2026-11-20 23:59:59', NULL, 'active'),

-- Loan 2: Sarah Chen borrowed Designing Data-Intensive Applications (Active, Overdue by ~5 days)
(2, 6, 3, 1, '2026-10-15 11:30:00', '2026-11-05 23:59:59', NULL, 'overdue'),

-- Loan 3: Michael Adebayo borrowed Introduction to Algorithms (Active, Overdue by ~8 days)
(3, 8, 4, 1, '2026-10-10 14:15:00', '2026-11-01 23:59:59', NULL, 'overdue'),

-- Loan 4: Priya Sharma borrowed Operating System Concepts (Active, Due in future)
(4, 13, 5, 1, '2026-11-08 09:45:00', '2026-11-22 23:59:59', NULL, 'active'),

-- Loan 5: David Kim borrowed Artificial Intelligence (Active, Due in future)
(5, 17, 6, 1, '2026-11-10 16:00:00', '2026-11-24 23:59:59', NULL, 'active'),

-- Loan 6: Alex Rivera borrowed Copy 36 (Active)
(6, 36, 2, 1, '2026-11-05 13:20:00', '2026-11-19 23:59:59', NULL, 'active'),

-- Loan 7: Returned on time historical loan (Alex Rivera)
(7, 4, 2, 1, '2026-09-01 10:00:00', '2026-09-15 23:59:59', '2026-09-14 15:30:00', 'returned'),

-- Loan 8: Returned late historical loan (Sarah Chen - generated fine)
(8, 7, 3, 1, '2026-09-05 11:00:00', '2026-09-19 23:59:59', '2026-09-24 16:00:00', 'returned'),

-- Loan 9: Returned late historical loan (Michael Adebayo - fine paid)
(9, 10, 4, 1, '2026-09-10 14:00:00', '2026-09-24 23:59:59', '2026-09-29 17:00:00', 'returned'),

-- Loan 10: Returned late historical loan (David Kim - fine waived)
(10, 14, 6, 1, '2026-09-15 12:00:00', '2026-09-29 23:59:59', '2026-10-04 14:30:00', 'returned');

-- ============================================================================
-- 9. SEED FINES (Unpaid, Paid, and Waived)
-- ============================================================================
INSERT INTO fines (fine_id, loan_id, user_id, amount, payment_status, paid_date) VALUES
-- Overdue fine from Loan 8 (5 days late * $1.00 = $5.00 unpaid)
(1, 8, 3, 5.00, 'unpaid', NULL),

-- Overdue fine from Loan 9 (5 days late * $1.00 = $5.00 paid)
(2, 9, 4, 5.00, 'paid', '2026-09-30 11:20:00'),

-- Overdue fine from Loan 10 (5 days late * $1.00 = $5.00 waived by admin)
(3, 10, 6, 5.00, 'waived', NULL);

-- ============================================================================
-- 10. SEED WAITLIST (FIFO Queue)
-- ============================================================================
INSERT INTO waitlist (waitlist_id, book_id, user_id, requested_at, status) VALUES
-- Sarah Chen is #1 in queue for Database System Concepts
(1, 1, 3, '2026-11-02 10:15:00', 'waiting'),
-- Michael Adebayo is #2 in queue for Database System Concepts
(2, 1, 4, '2026-11-03 14:20:00', 'waiting'),
-- David Kim was waiting for book 1 and got notified when a copy was reserved
(3, 1, 6, '2026-10-28 09:00:00', 'notified'),
-- Priya Sharma waiting for Designing Data-Intensive Applications
(4, 2, 5, '2026-11-06 16:45:00', 'waiting');

-- ============================================================================
-- 11. SEED STUDY ROOMS & BOOKINGS
-- ============================================================================
INSERT INTO study_rooms (room_id, room_name, capacity, has_whiteboard, has_power_outlets) VALUES
(1, 'Turing Collaborative Lab (Room 101)', 6, TRUE, TRUE),
(2, 'Lovelace Quiet Study (Room 102)', 2, FALSE, TRUE),
(3, 'Knuth Group Discussion (Room 201)', 8, TRUE, TRUE),
(4, 'Dijkstra Seminar Pod (Room 202)', 4, TRUE, TRUE);

INSERT INTO room_bookings (booking_id, room_id, user_id, booking_date, start_time, end_time, status) VALUES
(1, 1, 2, '2026-11-16', '09:00:00', '11:00:00', 'confirmed'),
(2, 1, 3, '2026-11-16', '13:00:00', '15:00:00', 'confirmed'),
(3, 2, 4, '2026-11-16', '10:00:00', '12:00:00', 'confirmed'),
(4, 3, 5, '2026-11-17', '14:00:00', '16:00:00', 'confirmed');

-- ============================================================================
-- 12. SEED BOOK REQUESTS & REQUEST VOTES (Crowdsourced Acquisition)
-- ============================================================================
INSERT INTO book_requests (request_id, title, author, isbn, requested_by, estimated_price, status, created_at) VALUES
(1, 'Building Microservices: Designing Fine-Grained Systems', 'Sam Newman', '978-1492034025', 2, 49.99, 'open', '2026-11-01 10:00:00'),
(2, 'Site Reliability Engineering: How Google Runs Production Systems', 'Niall Richard Murphy et al.', '978-1491929124', 3, 44.50, 'approved', '2026-11-02 11:30:00'),
(3, 'Rust Programming Language', 'Steve Klabnik and Carol Nichols', '978-1718503106', 4, 39.95, 'purchased', '2026-10-20 15:00:00');

INSERT INTO request_votes (request_id, user_id, voted_at) VALUES
(1, 2, '2026-11-01 10:01:00'),
(1, 3, '2026-11-01 12:45:00'),
(1, 4, '2026-11-02 09:10:00'),
(1, 5, '2026-11-03 14:00:00'),
(2, 3, '2026-11-02 11:31:00'),
(2, 4, '2026-11-02 16:20:00'),
(2, 6, '2026-11-03 11:00:00'),
(3, 4, '2026-10-20 15:05:00'),
(3, 2, '2026-10-21 08:30:00');

-- ============================================================================
-- 13. SEED AUDIT LOGS (Demonstrating DB Trigger Logging)
-- ============================================================================
INSERT INTO audit_logs (log_id, actor_id, action_type, target_table, target_record_id, old_value, new_value, timestamp) VALUES
(1, 1, 'FINE_WAIVED', 'fines', 3, '{"amount": 5.0, "status": "unpaid"}', '{"amount": 5.0, "status": "waived"}', '2026-10-05 14:35:00'),
(2, 1, 'BOOK_DELETED', 'books', 99, '{"title": "Deprecated Legacy Fortran 77", "isbn": "978-0000000001"}', NULL, '2026-10-12 09:15:00'),
(3, 1, 'COPY_STATUS_CHANGE', 'book_copies', 3, '{"barcode": "BC-1003", "status": "available"}', '{"barcode": "BC-1003", "status": "reserved"}', '2026-10-28 09:01:00');

