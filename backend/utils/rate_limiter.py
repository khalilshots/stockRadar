import json
import threading
import time
from collections import deque
from datetime import date

from config.settings import settings

_lock = threading.Lock()
_minute_windows: dict[str, deque] = {}


def _daily_limits() -> dict[str, int]:
    return {
        "alpha_vantage": settings.alpha_vantage_daily_limit,
        "newsapi": settings.newsapi_daily_limit,
        "fred": settings.fred_daily_limit,
    }


def _per_minute_limits() -> dict[str, int]:
    return {"finnhub": settings.finnhub_calls_per_minute}


def _load_usage() -> dict:
    path = settings.usage_path
    if not path.exists():
        return {}
    try:
        usage = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return usage if usage.get("date") == date.today().isoformat() else {}


def _save_usage(usage: dict) -> None:
    usage["date"] = date.today().isoformat()
    settings.usage_path.parent.mkdir(parents=True, exist_ok=True)
    settings.usage_path.write_text(json.dumps(usage))


def acquire(api: str) -> bool:
    """
    Reserve one call for this api. Returns False if the daily budget is spent.
    Per-minute limits block until a slot frees up instead of failing.
    """
    with _lock:
        daily = _daily_limits().get(api)
        if daily is not None:
            usage = _load_usage()
            used = usage.get(api, 0)
            if used >= daily:
                return False
            usage[api] = used + 1
            _save_usage(usage)

        per_minute = _per_minute_limits().get(api)
        if per_minute is None:
            return True
        window = _minute_windows.setdefault(api, deque())

    while True:
        with _lock:
            now = time.time()
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) < per_minute:
                window.append(now)
                return True
            wait = 60 - (now - window[0])
        time.sleep(max(wait, 0.05))


def remaining(api: str) -> int | None:
    daily = _daily_limits().get(api)
    if daily is None:
        return None
    return max(daily - _load_usage().get(api, 0), 0)
