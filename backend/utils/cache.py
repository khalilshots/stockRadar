import hashlib
import json
import time
from pathlib import Path

from config.settings import settings


def _path(namespace: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return settings.cache_dir / namespace / f"{digest}.json"


def read(namespace: str, key: str, ttl: int):
    """Return the cached value if it's younger than ttl seconds, else None."""
    path = _path(namespace, key)
    if not path.exists():
        return None
    try:
        entry = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - entry["saved_at"] > ttl:
        return None
    return entry["value"]


def write(namespace: str, key: str, value) -> None:
    path = _path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"saved_at": time.time(), "value": value}))
