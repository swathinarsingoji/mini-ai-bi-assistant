
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "sales_data.csv"
DB_PATH = BASE_DIR / "sales.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH)

    required = [
        "Transaction_Id", "Order_date", "Product",
        "Category", "Region", "Sales_channel",
        "Quantity", "Unit_price", "Discount_amount",
        "Status"
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing CSV columns: {missing}")

    df = df[required].copy()
    df["Order_date"] = pd.to_datetime(
        df["Order_date"], dayfirst=True, errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    for col in ["Quantity", "Unit_price", "Discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        "Transaction_Id", "Product", "Category",
        "Region", "Sales_channel", "Status"
    ]:
        df[col] = df[col].astype("string").str.strip()

    # Remove duplicate transaction IDs, keeping the first record.
    df = df.drop_duplicates(subset=["Transaction_Id"], keep="first")

    # Keep invalid numeric values as NULL rather than pretending
    # missing prices are zero.
    df["Quantity"] = df["Quantity"].where(df["Quantity"] >= 0)
    df["Unit_price"] = df["Unit_price"].where(df["Unit_price"] >= 0)
    df["Discount_amount"] = df["Discount_amount"].where(
        df["Discount_amount"] >= 0
    )

    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                transaction_id TEXT PRIMARY KEY,
                order_date TEXT,
                product TEXT,
                category TEXT,
                region TEXT,
                sales_channel TEXT,
                quantity REAL,
                unit_price REAL,
                discount_amount REAL,
                status TEXT
            )
        """)

        count = con.execute("SELECT COUNT(*) FROM sales").fetchone()[0]

        if count == 0:
            records = []
            for _, r in df.iterrows():
                records.append((
                    r["Transaction_Id"],
                    r["Order_date"] if pd.notna(r["Order_date"]) else None,
                    r["Product"] if pd.notna(r["Product"]) else None,
                    r["Category"] if pd.notna(r["Category"]) else None,
                    r["Region"] if pd.notna(r["Region"]) else None,
                    r["Sales_channel"] if pd.notna(r["Sales_channel"]) else None,
                    float(r["Quantity"]) if pd.notna(r["Quantity"]) else None,
                    float(r["Unit_price"]) if pd.notna(r["Unit_price"]) else None,
                    float(r["Discount_amount"])
                    if pd.notna(r["Discount_amount"]) else None,
                    r["Status"] if pd.notna(r["Status"]) else None,
                ))

            con.executemany("""
                INSERT OR IGNORE INTO sales VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)

        # Count records that cannot contribute to revenue.
        invalid = con.execute("""
            SELECT COUNT(*) FROM sales
            WHERE order_date IS NULL
               OR quantity IS NULL OR quantity <= 0
               OR unit_price IS NULL
               OR discount_amount IS NULL
        """).fetchone()[0]

        total = con.execute("SELECT COUNT(*) FROM sales").fetchone()[0]

    return {"records": total, "invalid_records": invalid}


# One consistent revenue rule for every analytics query:
# completed sales, positive quantity, known price and discount.
REVENUE = """
    (quantity * unit_price - discount_amount)
"""


def run_query(intent, params=None):
    params = params or {}

    eligible = """
        status = 'Completed'
        AND quantity > 0
        AND unit_price IS NOT NULL
        AND discount_amount IS NOT NULL
        AND order_date IS NOT NULL
    """

    queries = {
        "total_revenue": f"""
            SELECT ROUND(COALESCE(SUM({REVENUE}), 0), 2) AS revenue
            FROM sales WHERE {eligible}
        """,
        "top_product": f"""
            SELECT product, ROUND(SUM({REVENUE}), 2) AS revenue
            FROM sales
            WHERE {eligible} AND product IS NOT NULL
            GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 1
        """,
        "monthly_trend": f"""
            SELECT substr(order_date, 1, 7) AS month,
                   ROUND(SUM({REVENUE}), 2) AS revenue
            FROM sales WHERE {eligible}
            GROUP BY month ORDER BY month
        """,
        "top_region": f"""
            SELECT region, ROUND(SUM({REVENUE}), 2) AS revenue
            FROM sales
            WHERE {eligible} AND region IS NOT NULL
            GROUP BY region ORDER BY revenue DESC, region ASC LIMIT 1
        """,
        "month_comparison": f"""
            SELECT substr(order_date, 1, 7) AS month,
                   ROUND(SUM({REVENUE}), 2) AS revenue
            FROM sales
            WHERE {eligible} AND substr(order_date, 1, 7) IN (?, ?)
            GROUP BY month ORDER BY month
        """
    }

    if intent not in queries:
        raise ValueError("Unsupported question.")

    with get_connection() as con:
        if intent == "month_comparison":
            rows = con.execute(
                queries[intent],
                (params["month1"], params["month2"])
            ).fetchall()
        else:
            rows = con.execute(queries[intent]).fetchall()

    return [dict(row) for row in rows]
