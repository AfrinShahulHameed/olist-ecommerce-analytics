"""
Olist E-commerce End-to-End Case Study — Analysis Script
Dataset: Brazilian E-Commerce Public Dataset by Olist (Kaggle), 9 relational tables
Author: Afrin

Run: python3 load_db.py && python3 analysis.py
Produces: data.json (consumed by dashboard.html)
"""
import sqlite3
import pandas as pd
import numpy as np
import json
from scipy import stats

pd.set_option("display.width", 160)
conn = sqlite3.connect("olist.db")

# ---------------------------------------------------------------
# PHASE 2 — SQL ANALYSIS (queries live in sql_queries.sql; run here for real)
# ---------------------------------------------------------------
monthly_revenue = pd.read_sql("""
SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month,
       SUM(oi.price + oi.freight_value) AS revenue,
       COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('unavailable','canceled')
GROUP BY month ORDER BY month
""", conn)

delivery_stats = pd.read_sql("""
SELECT
  AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) AS avg_delivery_days,
  SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) * 1.0
    / COUNT(*) AS pct_late
FROM orders
WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL
""", conn)

seller_perf = pd.read_sql("""
SELECT s.seller_id,
       SUM(oi.price) AS revenue,
       COUNT(DISTINCT oi.order_id) AS orders,
       AVG(r.review_score) AS avg_review_score
FROM order_items oi
JOIN sellers s ON s.seller_id = oi.seller_id
LEFT JOIN order_reviews r ON r.order_id = oi.order_id
GROUP BY s.seller_id
""", conn)
top10_sellers = seller_perf.sort_values("revenue", ascending=False).head(10)
# bottom sellers: require >=5 orders so a single bad order doesn't dominate
bottom10_sellers = seller_perf[seller_perf["orders"] >= 5].sort_values("revenue", ascending=True).head(10)

category_revenue = pd.read_sql("""
SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
       SUM(oi.price) AS revenue,
       COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation ct ON ct.product_category_name = p.product_category_name
GROUP BY category ORDER BY revenue DESC
""", conn)

payment_breakdown = pd.read_sql("""
SELECT payment_type, COUNT(*) AS n_payments,
       AVG(payment_installments) AS avg_installments,
       SUM(payment_value) AS total_value
FROM order_payments GROUP BY payment_type ORDER BY total_value DESC
""", conn)

# ---------------------------------------------------------------
# PHASE 3 — PYTHON EDA: RFM, cohort retention, delay-vs-review
# ---------------------------------------------------------------
orders = pd.read_sql("SELECT * FROM orders", conn)
order_items = pd.read_sql("SELECT * FROM order_items", conn)
payments = pd.read_sql("SELECT * FROM order_payments", conn)
reviews = pd.read_sql("SELECT * FROM order_reviews", conn)
customers = pd.read_sql("SELECT * FROM customers", conn)

for col in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
    orders[col] = pd.to_datetime(orders[col], errors="coerce")

order_value = order_items.groupby("order_id")["price"].sum().reset_index()
orders_full = orders.merge(order_value, on="order_id", how="left").merge(
    customers[["customer_id", "customer_unique_id"]], on="customer_id", how="left"
)
delivered = orders_full[orders_full["order_status"] == "delivered"].dropna(subset=["order_purchase_timestamp"])

# --- RFM segmentation ---
snapshot_date = delivered["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
rfm = delivered.groupby("customer_unique_id").agg(
    Recency=("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
    Frequency=("order_id", "nunique"),
    Monetary=("price", "sum"),
).reset_index()

r_labels, f_labels, m_labels = range(4, 0, -1), range(1, 5), range(1, 5)
rfm["R_score"] = pd.qcut(rfm["Recency"], q=4, labels=r_labels, duplicates="drop").astype(int)
rfm["F_score"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=4, labels=f_labels, duplicates="drop").astype(int)
rfm["M_score"] = pd.qcut(rfm["Monetary"], q=4, labels=m_labels, duplicates="drop").astype(int)
rfm["RFM_sum"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

def segment(row):
    if row["RFM_sum"] >= 10:
        return "Champions"
    elif row["RFM_sum"] >= 8:
        return "Loyal"
    elif row["RFM_sum"] >= 6:
        return "Potential"
    elif row["R_score"] <= 2 and row["F_score"] <= 2:
        return "At-Risk"
    else:
        return "Lost"

rfm["segment"] = rfm.apply(segment, axis=1)
segment_summary = rfm.groupby("segment").agg(
    customers=("customer_unique_id", "count"), avg_monetary=("Monetary", "mean"), total_monetary=("Monetary", "sum")
).reset_index().sort_values("total_monetary", ascending=False)

# --- Cohort retention: repeat-purchase rate is essentially structural here ---
# (see limitations: customer_unique_id rarely repeats in this dataset — checked explicitly, not assumed)
repeat_customers = delivered.groupby("customer_unique_id")["order_id"].nunique()
pct_repeat = (repeat_customers > 1).mean()

delivered["cohort_month"] = delivered["order_purchase_timestamp"].dt.to_period("M").astype(str)
cohort_sizes = delivered.groupby("cohort_month")["customer_unique_id"].nunique().reset_index(name="new_customers")

# --- Delivery delay vs review score ---
delivered_with_dates = delivered.dropna(subset=["order_delivered_customer_date", "order_estimated_delivery_date"]).copy()
delivered_with_dates["delivery_delay_days"] = (
    delivered_with_dates["order_delivered_customer_date"] - delivered_with_dates["order_estimated_delivery_date"]
).dt.days
delivered_with_dates["is_late"] = delivered_with_dates["delivery_delay_days"] > 0
rev_merged = delivered_with_dates.merge(reviews[["order_id", "review_score"]], on="order_id", how="inner")

on_time_scores = rev_merged.loc[~rev_merged["is_late"], "review_score"]
late_scores = rev_merged.loc[rev_merged["is_late"], "review_score"]
t_stat, p_val = stats.ttest_ind(on_time_scores, late_scores, equal_var=False, nan_policy="omit")
corr, corr_p = stats.pointbiserialr(rev_merged["is_late"].astype(int), rev_merged["review_score"])

avg_score_by_late = rev_merged.groupby("is_late")["review_score"].mean()

# ---------------------------------------------------------------
# PHASE 7 — COUNTER-INTUITIVE FINDING
# Hypothesis to check: does a LONGER delivery route (customer state far
# from seller state) actually correlate with worse reviews, or is on-time-
# ness the real driver regardless of distance?
# ---------------------------------------------------------------
sellers = pd.read_sql("SELECT * FROM sellers", conn)
oi_full = order_items.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
oi_full = oi_full.merge(orders[["order_id", "customer_id"]], on="order_id", how="left")
oi_full = oi_full.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
oi_full["cross_state"] = oi_full["seller_state"] != oi_full["customer_state"]
cross_state_orders = oi_full.groupby("order_id")["cross_state"].max().reset_index()
rev_merged2 = rev_merged.merge(cross_state_orders, on="order_id", how="left")
same_state_scores = rev_merged2.loc[rev_merged2["cross_state"] == False, "review_score"]
cross_state_scores = rev_merged2.loc[rev_merged2["cross_state"] == True, "review_score"]
same_state_late_rate = rev_merged2.loc[rev_merged2["cross_state"] == False, "is_late"].mean()
cross_state_late_rate = rev_merged2.loc[rev_merged2["cross_state"] == True, "is_late"].mean()

print("=== MONTHLY REVENUE (last 5 months) ===")
print(monthly_revenue.tail())
print()
print("=== DELIVERY ===")
print(delivery_stats)
print()
print("=== TOP 5 SELLERS BY REVENUE ===")
print(top10_sellers.head())
print()
print("=== BOTTOM 5 SELLERS BY REVENUE (>=5 orders) ===")
print(bottom10_sellers.head())
print()
print("=== TOP 5 CATEGORIES BY REVENUE ===")
print(category_revenue.head())
print()
print("=== PAYMENT BREAKDOWN ===")
print(payment_breakdown)
print()
print("=== RFM SEGMENTS ===")
print(segment_summary)
print()
print(f"% customers with >1 order: {pct_repeat:.2%}")
print()
print("=== DELIVERY DELAY vs REVIEW SCORE ===")
print(avg_score_by_late)
print(f"t-test on-time vs late review score: t={t_stat:.3f}, p={p_val:.6f}")
print(f"point-biserial correlation (is_late, review_score): r={corr:.4f}, p={corr_p:.6f}")
print()
print("=== CROSS-STATE FINDING ===")
print(f"Same-state late rate: {same_state_late_rate:.2%}, avg review: {same_state_scores.mean():.2f}")
print(f"Cross-state late rate: {cross_state_late_rate:.2%}, avg review: {cross_state_scores.mean():.2f}")

output = {
    "monthly_revenue": monthly_revenue.to_dict(orient="records"),
    "delivery_stats": delivery_stats.to_dict(orient="records")[0],
    "top10_sellers": top10_sellers.fillna(0).to_dict(orient="records"),
    "bottom10_sellers": bottom10_sellers.fillna(0).to_dict(orient="records"),
    "category_revenue": category_revenue.head(15).to_dict(orient="records"),
    "payment_breakdown": payment_breakdown.to_dict(orient="records"),
    "segment_summary": segment_summary.to_dict(orient="records"),
    "pct_repeat_customers": round(float(pct_repeat), 4),
    "cohort_sizes": cohort_sizes.to_dict(orient="records"),
    "review_vs_delay": {
        "on_time_avg_score": round(float(on_time_scores.mean()), 3),
        "late_avg_score": round(float(late_scores.mean()), 3),
        "t_stat": round(float(t_stat), 3), "p_value": float(p_val),
        "correlation": round(float(corr), 4), "correlation_p": float(corr_p),
    },
    "insight": {
        "same_state_late_rate": round(float(same_state_late_rate), 4),
        "cross_state_late_rate": round(float(cross_state_late_rate), 4),
        "same_state_avg_review": round(float(same_state_scores.mean()), 3),
        "cross_state_avg_review": round(float(cross_state_scores.mean()), 3),
    },
    "total_customers": int(rfm.shape[0]),
    "total_revenue": round(float(monthly_revenue["revenue"].sum()), 2),
}
with open("data.json", "w") as f:
    json.dump(output, f, indent=2, default=str)
print("\nSaved data.json")
conn.close()
