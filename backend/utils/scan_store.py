import json
import os
import threading

from config.settings import settings

_lock = threading.Lock()


def save(record: dict) -> None:
    settings.scans_dir.mkdir(parents=True, exist_ok=True)
    path = settings.scans_dir / f"{record['id']}.json"
    tmp = path.with_suffix(".tmp")
    with _lock:
        tmp.write_text(json.dumps(record, default=str))
        os.replace(tmp, path)


def get(scan_id: str) -> dict | None:
    path = settings.scans_dir / f"{scan_id}.json"
    if not path.exists() or path.parent != settings.scans_dir:
        return None
    return json.loads(path.read_text())


def recent(limit: int = 20) -> list[dict]:
    if not settings.scans_dir.exists():
        return []
    paths = sorted(settings.scans_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    summaries = []
    for path in paths:
        try:
            r = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        summaries.append({k: r.get(k) for k in ("id", "strategy", "status", "started_at", "finished_at", "counts", "progress", "trigger")})
    return summaries


def latest() -> dict | None:
    items = recent(1)
    return get(items[0]["id"]) if items else None
