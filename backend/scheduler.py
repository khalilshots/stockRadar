import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from scan_runner import ScanBusy, runner
from strategies.strategy_manager import get_strategy

logger = logging.getLogger(__name__)
TZ = "America/New_York"


def _scan(session: str):
    strategy = get_strategy(settings.default_strategy)
    if not strategy:
        logger.warning(f"scheduled {session} scan skipped, no strategy named {settings.default_strategy!r}")
        return
    try:
        scan_id = runner.start(strategy, trigger=session)
        logger.info(f"{session} scan started: {scan_id}")
    except ScanBusy:
        logger.info(f"{session} scan skipped, another scan is running")


def start() -> BackgroundScheduler:
    """Weekday scans before the open, after the close and at night."""
    scheduler = BackgroundScheduler(timezone=TZ)
    for session, at in [("premarket", settings.premarket_scan), ("postmarket", settings.postmarket_scan), ("night", settings.night_scan)]:
        hour, minute = (int(x) for x in at.split(":"))
        scheduler.add_job(_scan, CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute, timezone=TZ),
                          args=[session], id=session, replace_existing=True)
    scheduler.start()
    return scheduler


def next_runs(scheduler: BackgroundScheduler | None) -> dict:
    if not scheduler:
        return {}
    return {job.id: job.next_run_time.isoformat() if job.next_run_time else None for job in scheduler.get_jobs()}
