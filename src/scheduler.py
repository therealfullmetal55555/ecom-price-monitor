"""
APScheduler setup for daily/hourly price checks.
Same pattern as Fares Korea case.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .config import SCHEDULE_HOUR, SCHEDULE_MINUTE, TIMEZONE
from .main import run_pipeline

logger = logging.getLogger(__name__)

def scheduled_job():
    logger.info(f"Scheduled job started at {datetime.now()}")
    try:
        result = run_pipeline(send_telegram=True)
        logger.info(f"Scheduled job finished: {result}")
    except Exception as e:
        logger.exception(f"Scheduled job failed: {e}")

def start_scheduler():
    tz = pytz.timezone(TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Daily job
    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone=tz),
        id="daily_price_check",
        name="Daily WB price monitor",
        replace_existing=True,
    )

    # Optional: hourly check for demo/testing (comment out in prod)
    # scheduler.add_job(
    #     scheduled_job,
    #     CronTrigger(minute=0, timezone=tz),
    #     id="hourly_price_check",
    #     name="Hourly check",
    #     replace_existing=True,
    # )

    logger.info(f"Scheduler started - daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} {TIMEZONE}")
    logger.info("Press Ctrl+C to exit")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
