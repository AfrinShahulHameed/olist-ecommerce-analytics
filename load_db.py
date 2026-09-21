"""
Olist E-commerce — load all 9 CSVs into a real SQLite database.
Phase 1 of the case study: get the data into a real DB before writing a query.
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect("olist.db")

TABLES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

for table, csv in TABLES.items():
    df = pd.read_csv(csv)
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"{table}: {len(df):,} rows")

# Indexes for the joins we're about to run repeatedly
conn.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_order ON order_payments(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_order ON order_reviews(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_items_seller ON order_items(seller_id)")
conn.commit()
conn.close()
print("olist.db built.")
