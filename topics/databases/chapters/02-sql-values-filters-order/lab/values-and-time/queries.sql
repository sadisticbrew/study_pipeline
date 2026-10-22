SELECT order_id, total_cents, discount_cents,
       total_cents - discount_cents AS payable_cents,
       typeof(total_cents - discount_cents) AS value_type
FROM orders WHERE discount_cents IS NOT NULL ORDER BY order_id;
SELECT 1299 / 100 AS whole_units, typeof(1299 / 100) AS value_type,
       1299 / 100.0 AS real_units, typeof(1299 / 100.0) AS real_type;
SELECT 0.1 + 0.2 AS sum, 0.3 AS target,
       0.1 + 0.2 = 0.3 AS equal, typeof(0.1 + 0.2) AS value_type;

SELECT order_id, amount, typeof(amount) AS value_type
FROM amounts ORDER BY order_id;
SELECT CAST('12x' AS INTEGER) AS converted,
       typeof(CAST('12x' AS INTEGER)) AS value_type;
SELECT 9223372036854775807 AS largest_integer,
       typeof(9223372036854775807) AS integer_type,
       9223372036854775807 + 1 AS overflow_result,
       typeof(9223372036854775807 + 1) AS result_type;

SELECT DISTINCT CAST(total_cents AS TEXT) AS amount_text FROM orders
ORDER BY amount_text COLLATE BINARY;
SELECT DISTINCT CAST(total_cents AS TEXT) AS amount_text FROM orders
ORDER BY CAST(amount_text AS INTEGER);

WITH spellings(label, submitted) AS (VALUES
    ('utc', '2026-10-19T09:00:00Z'),
    ('offset_same', '2026-10-19T11:00:00+02:00'),
    ('offset_earlier', '2026-10-19T09:30:00+02:00'))
SELECT label, submitted,
       strftime('%Y-%m-%dT%H:%M:%SZ', submitted) AS normalized_utc
FROM spellings ORDER BY submitted COLLATE BINARY;
SELECT datetime('2026-10-19T09:00:00Z') =
       datetime('2026-10-19T11:00:00+02:00') AS same_instant;
-- Every created_at has the same fixed-width UTC format and seconds precision.
SELECT order_id, created_at FROM orders
ORDER BY created_at COLLATE BINARY, order_id;
