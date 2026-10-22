CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    buyer TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    discount_cents INTEGER,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
-- created_at follows a fixed-format UTC convention, not a type constraint.
INSERT INTO orders VALUES
    (101, 'Ada', 1299, 0,    'pending', '2026-10-19T09:00:00Z'),
    (102, 'Bea', 1299, NULL, 'pending', '2026-10-19T09:05:00Z'),
    (103, 'Ada', 2500, 250,  'shipped', '2026-10-19T10:00:00Z'),
    (104, 'Cy',   800, NULL, 'pending', '2026-10-19T11:00:00Z'),
    (105, 'Dee', 1299, 0,    'pending', '2026-10-19T12:00:00Z');
