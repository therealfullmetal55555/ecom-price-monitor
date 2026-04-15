"""
Force a critical alert by temporarily lowering competitor price
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper import ProductInfo
from src.compare import load_my_prices, load_tracked_products, compare_prices, filter_critical_alerts
from src.alert_bot import MockAlerter

BASE_DIR = Path(__file__).resolve().parent.parent

my = load_my_prices(str(BASE_DIR / "demo-data" / "my-price-list.csv"))
tracked = load_tracked_products(str(BASE_DIR / "demo-data" / "tracked-products.csv"))

# Simulate competitor prices 15% cheaper
competitor_infos = []
for t in tracked:
    # Find my price for same category
    my_in_cat = [m for m in my if m.category == t.category]
    if not my_in_cat:
        continue
    my_price = my_in_cat[0].my_price
    comp_price = round(my_price * 0.85, 2)  # 15% cheaper -> should trigger
    competitor_infos.append(ProductInfo(
        nm_id=t.nm_id,
        name=f"Competitor product {t.nm_id}",
        brand="TestBrand",
        price=comp_price,
        basic_price=comp_price*1.2,
        in_stock=True,
        total_quantity=100,
        rating=4.5,
        feedbacks=500,
        url=f"https://www.wildberries.ru/catalog/{t.nm_id}/detail.aspx",
        checked_at="2026-09-28T09:00:00+00:00"
    ))

alerts = compare_prices(competitor_infos, my, tracked, threshold=0.05)
critical = filter_critical_alerts(alerts)

print(f"Total alerts: {len(alerts)}, Critical: {len(critical)}")
for a in critical:
    print(f"🚨 {a.message} | deviation {a.deviation_percent:.1f}%")

alerter = MockAlerter()
alerter.send_alerts_sync(alerts)
