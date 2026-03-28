import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Wildberries
WB_DEST = int(os.getenv("WB_DEST", "-1257786"))  # Moscow region default, see README
WB_DELAY = float(os.getenv("WB_DELAY_SECONDS", "1.5"))
WB_MAX_RPM = int(os.getenv("WB_MAX_REQUESTS_PER_MINUTE", "20"))
WB_API_URL = "https://card.wb.ru/cards/v4/detail"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Alert logic
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.05"))  # 5%

# Scheduler
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Tallinn")

# DB
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "price_history.db"))

# Headers - explicit User-Agent as ethical scraping practice
USER_AGENT = "PriceMonitor/1.0 (Portfolio Demo; +https://github.com/yourname/price-monitor) Python/httpx"
