"""
Comparison logic: my price list vs competitor prices
"""
import csv
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

from .scraper import ProductInfo

logger = logging.getLogger(__name__)

@dataclass
class MyProduct:
    sku: str
    name: str
    my_price: float
    category: str
    min_margin_price: Optional[float] = None  # don't go below this

@dataclass
class CompetitorProduct:
    nm_id: int
    category: str
    competitor_name: str
    notes: str = ""

@dataclass
class PriceAlert:
    my_product: MyProduct
    competitor: CompetitorProduct
    competitor_info: ProductInfo
    deviation_percent: float  # negative if competitor cheaper
    is_below_threshold: bool
    message: str

def load_my_prices(csv_path: str) -> List[MyProduct]:
    products = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                products.append(MyProduct(
                    sku=row['sku'].strip(),
                    name=row['name'].strip(),
                    my_price=float(row['my_price']),
                    category=row['category'].strip().lower(),
                    min_margin_price=float(row['min_margin_price']) if row.get('min_margin_price') else None
                ))
            except Exception as e:
                logger.warning(f"Skipping row {row}: {e}")
    logger.info(f"Loaded {len(products)} my products from {csv_path}")
    return products

def load_tracked_products(csv_path: str) -> List[CompetitorProduct]:
    products = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                products.append(CompetitorProduct(
                    nm_id=int(row['nm_id']),
                    category=row['category'].strip().lower(),
                    competitor_name=row.get('competitor_name', '').strip(),
                    notes=row.get('notes', '').strip()
                ))
            except Exception as e:
                logger.warning(f"Skipping row {row}: {e}")
    logger.info(f"Loaded {len(products)} tracked competitor products from {csv_path}")
    return products

def compare_prices(
    competitor_infos: List[ProductInfo],
    my_products: List[MyProduct],
    tracked: List[CompetitorProduct],
    threshold: float = 0.05
) -> List[PriceAlert]:
    """
    Compare competitor prices vs my prices by category.
    For each competitor product, find my products in same category and check deviation.
    
    threshold: if competitor price is threshold% cheaper than my price, trigger alert
    e.g. threshold=0.05 means competitor 5% cheaper triggers alert.
    """
    # Map nm_id -> CompetitorProduct
    tracked_map = {t.nm_id: t for t in tracked}
    # Map category -> list of MyProduct
    my_by_category: Dict[str, List[MyProduct]] = {}
    for mp in my_products:
        my_by_category.setdefault(mp.category, []).append(mp)

    alerts: List[PriceAlert] = []

    for c_info in competitor_infos:
        if c_info.error or c_info.price is None:
            logger.debug(f"Skipping {c_info.nm_id} - error or no price: {c_info.error}")
            continue
        c_meta = tracked_map.get(c_info.nm_id)
        if not c_meta:
            logger.debug(f"No meta for {c_info.nm_id}, skipping comparison")
            continue
        category = c_meta.category
        my_candidates = my_by_category.get(category, [])
        if not my_candidates:
            logger.debug(f"No my products in category {category} for competitor {c_info.nm_id}")
            continue

        # For simplicity, compare against cheapest my product in same category, or average?
        # Here: compare against each my product in category, but typically 1:1
        for my_prod in my_candidates:
            if my_prod.my_price <= 0:
                continue
            deviation = (c_info.price - my_prod.my_price) / my_prod.my_price  # negative if competitor cheaper
            is_below = deviation < -threshold

            if is_below:
                msg = (
                    f"🔻 Competitor cheaper in {category}: "
                    f"My '{my_prod.name}' {my_prod.my_price} RUB vs "
                    f"WB {c_info.nm_id} ({c_info.brand} {c_info.name[:40]}) {c_info.price} RUB "
                    f"({deviation*100:.1f}%)"
                )
            else:
                msg = (
                    f"✅ OK in {category}: My {my_prod.my_price} RUB vs Competitor {c_info.price} RUB "
                    f"({deviation*100:+.1f}%)"
                )

            alerts.append(PriceAlert(
                my_product=my_prod,
                competitor=c_meta,
                competitor_info=c_info,
                deviation_percent=deviation*100,
                is_below_threshold=is_below,
                message=msg
            ))

    # Sort: most critical (most negative deviation) first
    alerts.sort(key=lambda a: a.deviation_percent)
    return alerts

def filter_critical_alerts(alerts: List[PriceAlert]) -> List[PriceAlert]:
    return [a for a in alerts if a.is_below_threshold]

if __name__ == "__main__":
    # quick test with mock data
    from .scraper import ProductInfo
    my = [MyProduct(sku="MY001", name="Wireless Headphones X", my_price=3500, category="headphones")]
    tracked = [CompetitorProduct(nm_id=123, category="headphones", competitor_name="Test")]
    comp_infos = [ProductInfo(nm_id=123, name="Headphones Y", brand="Brand", price=3000, in_stock=True)]
    alerts = compare_prices(comp_infos, my, tracked, threshold=0.05)
    for a in alerts:
        print(a.message, "CRITICAL" if a.is_below_threshold else "OK")
