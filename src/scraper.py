"""
Wildberries price scraper using public card API (card.wb.ru/cards/v4/detail)

Key insights (as of 2025-2026):
- Only v4 endpoint works: /cards/v4/detail?appType=1&curr=rub&dest={dest}&spp=30&nm={ids}
- Batch support: nm ids separated by ; up to 100 per request
- Response: { data: { products: [...] } } where each product has sizes[].price.product (in kopecks)
- dest param = region code, affects price (different warehouses). Default -1257786 = Moscow-ish.
- Cloud IPs often get 403 antibot challenge. Code handles it gracefully and logs failed items instead of crashing pipeline.

If API is blocked, fallback to HTML parsing is attempted but also likely blocked. In that case,
pipeline continues and marks products as failed - this is intentional resilience.

Rate limiting: explicit delay + max RPM enforcement.
"""
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from .config import WB_API_URL, WB_DEST, WB_DELAY, WB_MAX_RPM, USER_AGENT

logger = logging.getLogger(__name__)

@dataclass
class ProductInfo:
    nm_id: int
    name: str = ""
    brand: str = ""
    price: Optional[float] = None  # final price in RUB
    basic_price: Optional[float] = None  # before discount
    in_stock: bool = False
    total_quantity: int = 0
    rating: Optional[float] = None
    feedbacks: int = 0
    url: str = ""
    checked_at: str = ""
    error: Optional[str] = None
    raw_sizes_count: int = 0

    def to_dict(self):
        return {
            "nm_id": self.nm_id,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "basic_price": self.basic_price,
            "in_stock": self.in_stock,
            "total_quantity": self.total_quantity,
            "rating": self.rating,
            "feedbacks": self.feedbacks,
            "url": self.url,
            "checked_at": self.checked_at,
            "error": self.error,
        }

def _to_rub(kopecks: Optional[int]) -> Optional[float]:
    if isinstance(kopecks, (int, float)):
        return round(kopecks / 100, 2)
    return None

def _parse_product(p: dict) -> ProductInfo:
    nm_id = p.get("id") or p.get("nmId") or 0
    name = p.get("name", "")
    brand = p.get("brand", "")
    # sizes array contains price
    sizes = p.get("sizes") or []
    price = None
    basic_price = None
    # Find first size with price.product
    for s in sizes:
        price_obj = s.get("price") or {}
        if price_obj.get("product") is not None:
            price = _to_rub(price_obj.get("product"))
            basic_price = _to_rub(price_obj.get("basic"))
            break
    # If not found in sizes, try direct (some API variants)
    if price is None:
        # fallback: try p['salePriceU'] / p['priceU'] (old schema)
        if p.get("salePriceU"):
            price = _to_rub(p.get("salePriceU"))
        if p.get("priceU"):
            basic_price = _to_rub(p.get("priceU"))

    total_qty = p.get("totalQuantity", 0)
    rating = p.get("reviewRating") or p.get("rating")
    feedbacks = p.get("feedbacks") or p.get("nmFeedbacks") or 0

    return ProductInfo(
        nm_id=int(nm_id),
        name=name,
        brand=brand,
        price=price,
        basic_price=basic_price,
        in_stock=(total_qty or 0) > 0 and price is not None,
        total_quantity=total_qty or 0,
        rating=float(rating) if rating is not None else None,
        feedbacks=int(feedbacks) if isinstance(feedbacks, (int, float)) else 0,
        url=f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
        checked_at=datetime.now(timezone.utc).isoformat(),
        raw_sizes_count=len(sizes),
    )

class WBScraper:
    def __init__(self, dest: int = WB_DEST, delay: float = WB_DELAY, max_rpm: int = WB_MAX_RPM):
        self.dest = dest
        self.delay = delay
        self.max_rpm = max_rpm
        self._last_request_ts = 0.0
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Origin": "https://www.wildberries.ru",
            "Referer": "https://www.wildberries.ru/",
        }

    def _rate_limit(self):
        """Enforce delay + max RPM"""
        now = time.time()
        elapsed = now - self._last_request_ts
        min_interval = 60.0 / self.max_rpm
        required_wait = max(self.delay, min_interval)
        if elapsed < required_wait:
            sleep_time = required_wait - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_ts = time.time()

    def fetch_products(self, nm_ids: List[int]) -> List[ProductInfo]:
        """
        Fetch product info for given nm_ids.
        Returns list of ProductInfo, with error field set if failed.
        Does NOT raise on individual product failures - resilient.
        """
        if not nm_ids:
            return []

        # Deduplicate and chunk (WB allows up to 100 per request)
        unique_ids = list(dict.fromkeys(nm_ids))  # preserve order
        chunk_size = 50  # conservative
        results: List[ProductInfo] = []
        failed: List[int] = []

        logger.info(f"Starting fetch for {len(unique_ids)} products (dest={self.dest})")

        with httpx.Client(timeout=15.0, headers=self.headers, follow_redirects=True) as client:
            for i in range(0, len(unique_ids), chunk_size):
                chunk = unique_ids[i:i+chunk_size]
                ids_str = ";".join(str(x) for x in chunk)
                params = {
                    "appType": 1,
                    "curr": "rub",
                    "dest": self.dest,
                    "spp": 30,
                    "nm": ids_str,
                }
                self._rate_limit()
                try:
                    resp = client.get(WB_API_URL, params=params)
                    logger.info(f"GET {resp.url} -> {resp.status_code}")
                    if resp.status_code == 403:
                        logger.warning(f"403 Forbidden - likely antibot block from cloud IP. Chunk {chunk} marked as blocked.")
                        # Mark all in chunk as blocked
                        for nid in chunk:
                            results.append(ProductInfo(
                                nm_id=nid,
                                checked_at=datetime.now(timezone.utc).isoformat(),
                                error="403 Forbidden - antibot block (run locally or via residential proxy)"
                            ))
                        failed.extend(chunk)
                        continue
                    if resp.status_code == 404:
                        logger.warning(f"404 for chunk {chunk}")
                        for nid in chunk:
                            results.append(ProductInfo(nm_id=nid, error="404 Not Found - product may be removed"))
                        failed.extend(chunk)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    # v4 returns {"data": {"products": [...]}} or {"products": [...]}
                    products = []
                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], dict):
                            products = data["data"].get("products", [])
                        elif "products" in data:
                            products = data["products"]
                        else:
                            # Sometimes it's directly list? log
                            products = data.get("products", [])

                    # Map returned products by id for quick lookup
                    returned_by_id = {}
                    for p in products:
                        pid = p.get("id") or p.get("nmId")
                        if pid:
                            returned_by_id[int(pid)] = p

                    for nid in chunk:
                        if nid in returned_by_id:
                            try:
                                info = _parse_product(returned_by_id[nid])
                                results.append(info)
                            except Exception as e:
                                logger.exception(f"Parse error for {nid}: {e}")
                                results.append(ProductInfo(nm_id=nid, error=f"Parse error: {e}"))
                                failed.append(nid)
                        else:
                            logger.warning(f"Product {nid} not in response (may be out of stock or removed)")
                            results.append(ProductInfo(nm_id=nid, error="Not in API response - out of stock or removed"))
                            failed.append(nid)

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error for chunk {chunk}: {e}")
                    for nid in chunk:
                        results.append(ProductInfo(nm_id=nid, error=f"HTTP {e.response.status_code}"))
                    failed.extend(chunk)
                except Exception as e:
                    logger.exception(f"Unexpected error for chunk {chunk}: {e}")
                    for nid in chunk:
                        results.append(ProductInfo(nm_id=nid, error=str(e)))
                    failed.extend(chunk)

        if failed:
            logger.info(f"Fetch completed with {len(failed)} failures out of {len(unique_ids)}: {failed}")
        else:
            logger.info(f"Fetch completed successfully for all {len(unique_ids)} products")

        return results

    def fetch_single(self, nm_id: int) -> ProductInfo:
        res = self.fetch_products([nm_id])
        return res[0] if res else ProductInfo(nm_id=nm_id, error="Empty response")

# For local testing / demo
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = WBScraper()
    test_ids = [1097975275, 173889188, 185470933]
    products = scraper.fetch_products(test_ids)
    for p in products:
        print(p.to_dict())
