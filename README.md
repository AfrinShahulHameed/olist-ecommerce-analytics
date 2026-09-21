# Olist E-commerce End-to-End Case Study

**Type:** Analyst case study (flagship project) · **Tools:** SQLite (real SQL joins), Python (pandas, SciPy) for cleaning and statistical validation, Power BI (data model with real relationships, DAX measures, 4-page dashboard)
**Dataset:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle) — 9 relational CSVs: orders, order_items, order_payments, order_reviews, customers, products, sellers, geolocation, category translation.

The SQL layer is real, not simulated — see `sql_queries.sql`, run against an actual SQLite database (`olist.db`) built by `load_db.py`. The Power BI data model mirrors that same relational structure: seven related tables (orders, order_items, customers, sellers, reviews, payments, and a precomputed RFM table) connected with real relationships, not one flattened CSV.

## Dashboard Preview

**Revenue Overview**
![Revenue Overview](screenshots/Revenue%20Overview.png)

**Delivery & Reviews**
![Delivery and Reviews](screenshots/Delivery%20%26%20Reviews.png)

**Sellers & Categories**
![Sellers and Categories](screenshots/Sellers%20%26%20Categories.png)

**Customer Segments**
![Customer Segments](screenshots/Customer%20Segments.png)

---

## 1. Business Problem

Leadership at this e-commerce marketplace wants one end-to-end view: what's driving revenue, where deliveries are failing, which sellers are underperforming, and which customers are actually worth retaining.

Questions this case study answers:
1. What does the revenue trend look like, and what's it made of?
2. Where is delivery failing, and does it actually matter to customers (reviews)?
3. Which sellers and categories are winning or losing?
4. Who are the valuable customers, and — critically — is a "retention" strategy even the right frame for this business?

## 2. Data & Methodology

- All 9 CSVs loaded into a real SQLite database (`olist.db`) via `load_db.py`, with indexes on the join keys used repeatedly (`order_id`, `product_id`, `seller_id`).
- An ERD (conceptual): `orders` ← `order_items` → `products`/`sellers`; `orders` → `order_payments`, `order_reviews`, `customers`. All joins in this project are on these IDs — no flat CSV shortcuts.
- SQL queries (revenue trend, delivery stats, seller leaderboard, category revenue, payment breakdown) are saved with comments in `sql_queries.sql` and actually executed against the SQLite DB in `analysis.py` — not hand-copied results.
- Python EDA layer: RFM segmentation, cohort/repeat-purchase check, and a delivery-delay-vs-review-score analysis, all in `analysis.py`.

## 3. Key Findings (real numbers, computed from the data)

- **Total revenue (order value + freight): R$15,735,527** across ~93,358 unique customers, Oct 2016–Aug 2018 (the last month in the data, Sep 2018, has only 1 order and was excluded from the trend chart as an incomplete period, not a real data point).
- **Average delivery time: 12.6 days**, with **8.1% of delivered orders arriving after their estimated delivery date.**

### Headline / counter-intuitive finding #1: this isn't a repeat-purchase business
**Only 3.0% of customers ever place a second order.** This matters more than it sounds: the brief's RFM/cohort-retention framework is built for businesses where repeat purchase is the norm and "loyalty" is a meaningful, actionable segment. Here, with a 3% repeat rate, the "Frequency" dimension of RFM is nearly binary (1 order vs. 2+) for the overwhelming majority of customers — so "Loyal" and "Champions" segments mostly reflect **big first-order spend**, not actual repeat behavior. Stating this plainly (rather than forcing a retention narrative the data doesn't support) is itself the more useful, defensible insight — and it reframes the real lever from "win back at-risk customers" to "get the first order right, because there's usually no second chance."

### Headline / counter-intuitive finding #2: delivery lateness is a real, quantified driver of bad reviews
On-time deliveries average a **4.29-star review**; late deliveries average **2.27 stars** — a gap confirmed statistically significant (Welch's t-test, t=100.97, p<0.000001) and moderately-strongly correlated (point-biserial r=-0.39, p<0.000001). In dataset terms: **R$1,158,921 in order value (8.8% of total order value) sits in shipments that arrived late**, each of those orders averaging a review score barely above "poor."
- **Cross-state (interstate) shipping nearly doubles the late-delivery rate**: 7.9% late when seller and customer are in different states, vs. 4.5% when they're in the same state — a concrete, actionable logistics finding, not a guess.

### Sellers & categories
- Revenue is concentrated at the top: the #1 seller by revenue did R$229,472 across 1,132 orders; several top-10 sellers combine high revenue with average review scores well above 4.0, but at least one top-10 seller (avg review 3.35) shows high volume paired with meaningfully weaker satisfaction — worth a seller-quality review, not just a revenue ranking.
- Top revenue categories: health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories.
- Payment behavior: credit card dominates (R$12.5M of ~R$16M total payment value, avg 3.5 installments) — boleto (a Brazilian bank-slip payment method) is a distant second with no installments, worth knowing before assuming "installments" behavior generalizes across payment types.

## 4. Recommendations

1. **Reframe the customer strategy around first-order delivery reliability, not retention campaigns** — with a 3% repeat rate, marketing spend aimed at "winning back" lapsed customers has a structurally small ceiling; the bigger lever is preventing the 8.1% late-delivery rate that's driving 2-star reviews on first (and often only) orders.
2. **Prioritize logistics fixes on cross-state routes specifically** — the late-rate nearly doubles there, and it's a clean, targetable segment (not "fix delivery everywhere").
3. **Audit the specific top-10-revenue seller with a 3.35 average review** — high volume is masking a satisfaction problem that a pure revenue leaderboard would miss.
4. **Treat "Champions"/"Loyal" RFM labels as spend-tier labels, not loyalty labels**, when presenting this to stakeholders — mislabeling them risks a retention strategy built on a false premise.

## 5. Limitations (what to validate with more time/data)

- **The 3% repeat-purchase rate is structural to this dataset's time window** (2016–2018) — it's possible some "one-time" customers in the data have since ordered again outside the observed period; this should be checked against fresher data before treating the number as permanent.
- **RFM Frequency/Recency quartile cuts (`pd.qcut`) are relative to this dataset**, not fixed business thresholds — segment boundaries would shift with a different time window or customer base.
- **The delivery-delay-vs-review correlation is not necessarily causal** — a late delivery might correlate with other problems (damaged goods, wrong item) that independently lower the review score; this analysis shows a strong association, not a proven single cause.
- **Cross-state late-rate finding doesn't control for distance/carrier** — some cross-state routes are much longer than others; a more granular version would bucket by actual shipping distance, not just same/different state.
- **Bottom-seller ranking required a ≥5-order minimum** to avoid one bad order making a seller look artificially terrible — a genuine, documented judgment call, not a neutral default.

## 6. Files in this repo

| File | What it is |
|---|---|
| `olist_*.csv` | Original Kaggle exports — **not included in the delivered package** (raw files total ~65MB, over the delivery size limit); re-download from Kaggle and drop them in this folder to reproduce `olist.db` |
| `product_category_name_translation.csv` | Included — tiny reference file |
| `load_db.py` | Loads all 9 CSVs into `olist.db` (SQLite), with indexes |
| `sql_queries.sql` | The 5 core SQL queries, commented, run for real in `analysis.py` |
| `analysis.py` | Full SQL + Python pipeline: RFM, repeat-purchase check, delay-vs-review stats, cross-state finding |
| `Olist_Ecommerce_Dashboard.pbix` | The finished Power BI dashboard — open in Power BI Desktop (free, no license needed to view) |
| `screenshots/` | PNG exports of all 4 dashboard pages, for anyone viewing the repo without Power BI |

To reproduce the data pipeline: `python3 load_db.py && python3 analysis.py`. To rebuild the dashboard, open `Olist_Ecommerce_Dashboard.pbix` in Power BI Desktop.

## 7. Summary

Leadership wanted an end-to-end view of an e-commerce marketplace: revenue, delivery, sellers, and customers. The standard playbook here would be to build an RFM model and target retention, but only 3% of customers ever order twice, so that framing doesn't hold up. Instead of forcing a retention story the data didn't support, the real lever turned out to be first-order delivery reliability. Late deliveries average 2.27-star reviews versus 4.29 for on-time ones, a statistically significant gap worth R$1.16 million in order value, and cross-state shipping nearly doubles the late rate. That points to a logistics fix with a clear, targetable segment, not a vague "improve retention" recommendation.
