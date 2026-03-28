import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from .config import DB_PATH
from .scraper import ProductInfo

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nm_id INTEGER NOT NULL,
    name TEXT,
    brand TEXT,
    price REAL,
    basic_price REAL,
    in_stock BOOLEAN,
    total_quantity INTEGER,
    rating REAL,
    feedbacks INTEGER,
    url TEXT,
    checked_at TEXT NOT NULL,
    error TEXT,
    dest INTEGER
);
CREATE INDEX IF NOT EXISTS idx_nm_id_checked ON price_history(nm_id, checked_at);
"""

def get_connection(db_path: str = DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    conn.executescript(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()
    logger.info(f"DB initialized at {db_path}")

def save_snapshot(products: List[ProductInfo], db_path: str = DB_PATH, dest: int = -1257786):
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for p in products:
        rows.append((
            p.nm_id,
            p.name,
            p.brand,
            p.price,
            p.basic_price,
            int(p.in_stock) if p.in_stock is not None else 0,
            p.total_quantity,
            p.rating,
            p.feedbacks,
            p.url,
            p.checked_at or now,
            p.error,
            dest
        ))
    cur.executemany("""
        INSERT INTO price_history
        (nm_id, name, brand, price, basic_price, in_stock, total_quantity, rating, feedbacks, url, checked_at, error, dest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    logger.info(f"Saved {len(rows)} records to {db_path}")

def get_history(nm_id: int, days: int = 30, db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM price_history
        WHERE nm_id = ?
        ORDER BY checked_at DESC
        LIMIT ?
    """, (nm_id, days*10))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_prices(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    # Latest per nm_id
    cur.execute("""
        SELECT p1.* FROM price_history p1
        INNER JOIN (
            SELECT nm_id, MAX(checked_at) as max_checked FROM price_history GROUP BY nm_id
        ) p2 ON p1.nm_id = p2.nm_id AND p1.checked_at = p2.max_checked
        ORDER BY p1.nm_id
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_price_dynamics(days: int = 7, db_path: str = DB_PATH):
    """Return daily avg price per nm_id for last N days"""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT nm_id, name, DATE(checked_at) as date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as checks
        FROM price_history
        WHERE price IS NOT NULL AND DATE(checked_at) >= DATE('now', ?)
        GROUP BY nm_id, DATE(checked_at)
        ORDER BY nm_id, date
    """, (f'-{days} days',))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_history(db_path: str = DB_PATH, limit: int = 1000):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM price_history ORDER BY checked_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
