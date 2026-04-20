"""
Seed DB with synthetic 5-day history from demo-data/price-history-sample.csv
So portfolio can show dynamics even if WB API blocked in cloud.
"""
import csv
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import init_db, get_connection
from src.config import DB_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_CSV = BASE_DIR / "demo-data" / "price-history-sample.csv"

def seed_from_sample():
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    cur = conn.cursor()
    # Clear old
    cur.execute("DELETE FROM price_history")
    
    with open(SAMPLE_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # parse date as checked_at at 09:00 UTC
            date_str = row['date']
            dt = datetime.fromisoformat(date_str + "T09:00:00+00:00")
            rows.append((
                int(row['nm_id']),
                row['name'],
                row['brand'],
                float(row['price']),
                float(row['basic_price']),
                1,  # in_stock
                random.randint(10, 200),
                round(random.uniform(4.2, 4.9), 1),
                random.randint(100, 2000),
                f"https://www.wildberries.ru/catalog/{row['nm_id']}/detail.aspx",
                dt.isoformat(),
                None,
                -1257786
            ))
    cur.executemany("""
        INSERT INTO price_history
        (nm_id, name, brand, price, basic_price, in_stock, total_quantity, rating, feedbacks, url, checked_at, error, dest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    print(f"Seeded {len(rows)} rows from {SAMPLE_CSV}")

    # Also add some random variation for last 2 days to simulate real run
    cur.execute("SELECT COUNT(*) as c FROM price_history")
    count = cur.fetchone()['c']
    print(f"Total in DB: {count}")

    conn.close()

def seed_random_5_days():
    """Generate random 5-day history for all tracked products if sample not enough"""
    from src.compare import load_tracked_products
    tracked_path = BASE_DIR / "demo-data" / "tracked-products.csv"
    tracked = load_tracked_products(str(tracked_path))
    
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM price_history")
    
    base_prices = {
        1097975275: 2890,
        173889188: 1890,
        185470933: 1590,
        173592402: 2590,
        212997408: 1490,
        192707003: 5290,
        199124867: 3290,
        168300345: 1390,
    }
    
    rows = []
    for day_offset in range(5, 0, -1):
        dt = datetime.now(timezone.utc) - timedelta(days=day_offset)
        dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
        for t in tracked:
            base = base_prices.get(t.nm_id, 2000)
            # random walk +-10%
            variation = random.uniform(-0.1, 0.05)
            # Simulate one day where competitor drops
            if day_offset == 2 and t.nm_id in [173592402, 168300345]:
                variation = -0.15  # big drop
            price = round(base * (1 + variation), 2)
            rows.append((
                t.nm_id,
                f"Product {t.nm_id}",
                "DemoBrand",
                price,
                round(price * 1.3, 2),
                1,
                random.randint(5, 300),
                round(random.uniform(4.0, 5.0), 2),
                random.randint(50, 3000),
                f"https://www.wildberries.ru/catalog/{t.nm_id}/detail.aspx",
                dt.isoformat(),
                None,
                -1257786
            ))
    cur.executemany("""
        INSERT INTO price_history
        (nm_id, name, brand, price, basic_price, in_stock, total_quantity, rating, feedbacks, url, checked_at, error, dest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} random rows for {len(tracked)} products x 5 days")

if __name__ == "__main__":
    if SAMPLE_CSV.exists():
        seed_from_sample()
    else:
        seed_random_5_days()
