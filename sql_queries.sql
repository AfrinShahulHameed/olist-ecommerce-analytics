-- Olist E-commerce End-to-End Case Study — SQL Analysis
-- Every query here is run for real against olist.db (SQLite) in analysis.py.
-- Saved separately, with comments, per the brief: "this file itself becomes a deliverable."

-- 1. Monthly revenue trend (join orders + order_items + payments)
SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month,
       SUM(oi.price + oi.freight_value) AS revenue,
       COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('unavailable', 'canceled')
GROUP BY month
ORDER BY month;

-- 2. Average delivery time and % of late deliveries (actual vs estimated)
SELECT
  AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) AS avg_delivery_days,
  SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) * 1.0
    / COUNT(*) AS pct_late
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;

-- 3. Top 10 and bottom 10 sellers, by revenue and by average review score
SELECT s.seller_id,
       SUM(oi.price) AS revenue,
       COUNT(DISTINCT oi.order_id) AS orders,
       AVG(r.review_score) AS avg_review_score
FROM order_items oi
JOIN sellers s ON s.seller_id = oi.seller_id
LEFT JOIN order_reviews r ON r.order_id = oi.order_id
GROUP BY s.seller_id
ORDER BY revenue DESC
LIMIT 10;
-- (bottom 10: same query, ORDER BY revenue ASC, with a minimum order-count filter
--  to avoid one-order sellers dominating the "worst" list — see analysis.py)

-- 4. Revenue by product category (English names via category_translation)
SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
       SUM(oi.price) AS revenue,
       COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation ct ON ct.product_category_name = p.product_category_name
GROUP BY category
ORDER BY revenue DESC;

-- 5. Payment method breakdown (type, installments)
SELECT payment_type,
       COUNT(*) AS n_payments,
       AVG(payment_installments) AS avg_installments,
       SUM(payment_value) AS total_value
FROM order_payments
GROUP BY payment_type
ORDER BY total_value DESC;
