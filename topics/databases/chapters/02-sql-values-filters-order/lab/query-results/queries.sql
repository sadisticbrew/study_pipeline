SELECT order_id, buyer, total_cents, discount_cents, status, created_at
FROM orders ORDER BY order_id;

SELECT order_id, total_cents - discount_cents AS payable_cents
FROM orders ORDER BY order_id;
SELECT buyer FROM orders ORDER BY buyer COLLATE BINARY, order_id;
SELECT DISTINCT buyer FROM orders ORDER BY buyer COLLATE BINARY;

SELECT order_id, discount_cents, discount_cents = 0 AS is_zero,
       NOT (discount_cents = 0) AS not_zero,
       discount_cents IS NULL AS is_missing,
       discount_cents IS NOT NULL AS is_recorded
FROM orders ORDER BY order_id;
SELECT order_id FROM orders WHERE discount_cents = 0 ORDER BY order_id;
SELECT order_id FROM orders WHERE NOT (discount_cents = 0) ORDER BY order_id;
SELECT order_id FROM orders WHERE discount_cents IS NULL ORDER BY order_id;
SELECT order_id FROM orders WHERE discount_cents IS NOT NULL ORDER BY order_id;
SELECT NULL = NULL AS null_equals_null, NULL + 1 AS null_plus_one;

-- Tied totals alone do not specify the order inside each tied group.
SELECT order_id, total_cents FROM orders WHERE status = 'pending'
ORDER BY total_cents DESC;
SELECT order_id, total_cents FROM orders WHERE status = 'pending'
ORDER BY total_cents DESC, order_id ASC LIMIT 2;

SELECT order_id, buyer, total_cents - discount_cents AS payable_cents
FROM orders
WHERE status = 'pending' AND discount_cents = 0
ORDER BY total_cents DESC, order_id ASC
LIMIT 2;

SELECT order_id, discount_cents FROM orders
ORDER BY discount_cents ASC, order_id;
SELECT order_id, discount_cents FROM orders
ORDER BY discount_cents DESC, order_id;
SELECT order_id, discount_cents FROM orders
ORDER BY discount_cents ASC NULLS LAST, order_id;
SELECT order_id, discount_cents FROM orders
ORDER BY discount_cents DESC NULLS FIRST, order_id;
