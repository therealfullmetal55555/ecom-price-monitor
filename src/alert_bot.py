"""
Telegram alerts - supports both sync (requests/httpx) and async (aiogram v3)
For portfolio: simple sync version works without running bot polling, just sends message via Bot API.

Usage:
    alerter = TelegramAlerter(token, chat_id)
    alerter.send_alerts_sync(critical_alerts)
"""
import logging
from typing import List
import httpx

from .compare import PriceAlert

logger = logging.getLogger(__name__)

class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def _format_alert_message(self, alerts: List[PriceAlert], include_ok: bool = False) -> str:
        if not alerts:
            return "✅ Price monitor check completed - no critical deviations."

        critical = [a for a in alerts if a.is_below_threshold]
        ok = [a for a in alerts if not a.is_below_threshold]

        lines = []
        lines.append(f"📊 *Price Monitor Report* - {len(alerts)} comparisons")
        lines.append("")

        if critical:
            lines.append(f"🚨 *Critical: {len(critical)} competitors cheaper*")
            for a in critical[:10]:  # limit to 10 to avoid too long message
                # Escape markdown? Keep simple
                lines.append(
                    f"• _{a.competitor.category}_ | "
                    f"My: *{a.my_product.name}* `{a.my_product.my_price}₽` "
                    f"vs Comp: [{a.competitor_info.nm_id}](https://www.wildberries.ru/catalog/{a.competitor_info.nm_id}/detail.aspx) "
                    f"`{a.competitor_info.price}₽` "
                    f"({a.deviation_percent:.1f}%)\n"
                    f"  {a.competitor_info.brand} {a.competitor_info.name[:60]}"
                )
            lines.append("")
        else:
            lines.append("✅ No critical undercuts detected.")
            lines.append("")

        if include_ok and ok:
            lines.append(f"ℹ️ Other checks ({len(ok)}):")
            for a in ok[:5]:
                lines.append(f"• {a.my_product.category}: {a.my_product.my_price}₽ vs {a.competitor_info.price}₽ ({a.deviation_percent:+.1f}%)")

        lines.append("")
        lines.append(f"_Threshold: competitor cheaper by > {abs(critical[0].deviation_percent) if critical else 5}% triggers alert_")
        return "\n".join(lines)

    def send_message_sync(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram token or chat_id not set - skipping send")
            print(f"[MOCK TELEGRAM] Would send to {self.chat_id}:\n{text}\n")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    logger.info(f"Telegram message sent to {self.chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {data}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_alerts_sync(self, alerts: List[PriceAlert], include_ok: bool = False) -> bool:
        critical = [a for a in alerts if a.is_below_threshold]
        if not critical:
            logger.info("No critical alerts to send")
            # Optionally still send summary? For demo we send only if critical, but can be configured
            # For portfolio demo we want at least one alert to show
            if not include_ok:
                return False

        message = self._format_alert_message(alerts, include_ok=include_ok)
        return self.send_message_sync(message)

    async def send_alerts_async(self, alerts: List[PriceAlert], include_ok: bool = False):
        """Aiogram v3 async version - for use in bot polling"""
        try:
            from aiogram import Bot
            from aiogram.enums import ParseMode
        except ImportError:
            logger.error("aiogram not installed, falling back to sync")
            return self.send_alerts_sync(alerts, include_ok)

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials missing")
            return False

        message = self._format_alert_message(alerts, include_ok=include_ok)
        bot = Bot(token=self.bot_token)
        try:
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info("Async Telegram message sent")
            return True
        except Exception as e:
            logger.error(f"Async send failed: {e}")
            return False
        finally:
            await bot.session.close()

# Mock alerter for local testing without Telegram
class MockAlerter:
    def send_alerts_sync(self, alerts, include_ok=False):
        print("\n=== MOCK ALERT ===")
        for a in alerts:
            print(a.message)
        print("=== END MOCK ===\n")
        return True
