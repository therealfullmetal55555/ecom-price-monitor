"""
Main pipeline: fetch -> save -> compare -> alert
"""
import logging
import sys
from pathlib import Path

# Ensure src is importable when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DB_PATH, ALERT_THRESHOLD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WB_DEST
from src.scraper import WBScraper
from src.db import init_db, save_snapshot, get_latest_prices
from src.compare import load_my_prices, load_tracked_products, compare_prices, filter_critical_alerts
from src.alert_bot import TelegramAlerter, MockAlerter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/monitor.log")
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

def run_pipeline(send_telegram: bool = True, db_path: str = DB_PATH, threshold: float = ALERT_THRESHOLD):
    logger.info("=== Price Monitor Pipeline Started ===")
    init_db(db_path)

    # Load data
    tracked_path = BASE_DIR / "demo-data" / "tracked-products.csv"
    my_prices_path = BASE_DIR / "demo-data" / "my-price-list.csv"

    if not tracked_path.exists():
        logger.error(f"Tracked products file not found: {tracked_path}")
        return {"status": "error", "reason": "tracked file missing"}

    if not my_prices_path.exists():
        logger.error(f"My price list not found: {my_prices_path}")
        return {"status": "error", "reason": "my price list missing"}

    tracked = load_tracked_products(str(tracked_path))
    my_products = load_my_prices(str(my_prices_path))

    nm_ids = [t.nm_id for t in tracked]
    logger.info(f"Tracking {len(nm_ids)} competitor products in {len(set(t.category for t in tracked))} categories")

    # Scrape
    scraper = WBScraper(dest=WB_DEST)
    competitor_infos = scraper.fetch_products(nm_ids)

    # Save to DB even if some failed
    save_snapshot(competitor_infos, db_path=db_path, dest=WB_DEST)

    success_count = len([p for p in competitor_infos if not p.error and p.price is not None])
    failed_count = len(competitor_infos) - success_count
    logger.info(f"Scrape result: {success_count} success, {failed_count} failed")

    if failed_count == len(competitor_infos):
        logger.warning("All products failed - likely antibot block. Check logs. Pipeline continues with historical data if available.")
        # Try to use latest from DB for comparison to still demonstrate flow
        latest = get_latest_prices(db_path)
        # Convert latest DB rows to ProductInfo-like for comparison (simplified)
        # For now, just return
        return {
            "status": "partial",
            "success": success_count,
            "failed": failed_count,
            "alerts": [],
            "message": "All fetches failed - antibot block, check README for workaround"
        }

    # Compare
    alerts = compare_prices(competitor_infos, my_products, tracked, threshold=threshold)
    critical = filter_critical_alerts(alerts)

    logger.info(f"Comparison: {len(alerts)} total, {len(critical)} critical")

    for a in alerts:
        log_level = logging.WARNING if a.is_below_threshold else logging.INFO
        logger.log(log_level, a.message)

    # Alert
    if send_telegram:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            alerter = TelegramAlerter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        else:
            logger.info("Telegram credentials not set, using MockAlerter")
            alerter = MockAlerter()

        if critical:
            alerter.send_alerts_sync(alerts, include_ok=False)
            logger.info(f"Sent {len(critical)} critical alerts to Telegram")
        else:
            # For demo, you might want to send summary anyway
            logger.info("No critical alerts to send")
            # Uncomment to send OK summary:
            # alerter.send_alerts_sync(alerts, include_ok=True)

    logger.info("=== Pipeline Finished ===")
    return {
        "status": "success",
        "success": success_count,
        "failed": failed_count,
        "total_alerts": len(alerts),
        "critical_alerts": len(critical),
        "alerts": [a.message for a in critical],
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WB Price Monitor")
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram alerts")
    parser.add_argument("--threshold", type=float, default=ALERT_THRESHOLD, help="Alert threshold (e.g. 0.05)")
    args = parser.parse_args()

    result = run_pipeline(send_telegram=not args.no_telegram, threshold=args.threshold)
    print(result)
