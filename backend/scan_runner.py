import threading

from agents.orchestrator import Sources, new_record, run_scan
from strategies.strategy_manager import Strategy
from utils import scan_store


class ScanBusy(Exception):
    pass


class ScanRunner:
    """Runs one scan at a time in a background thread and saves progress as it goes."""

    def __init__(self, sources_factory=None):
        self._lock = threading.Lock()
        self._current: str | None = None
        self._sources_factory = sources_factory

    @property
    def current(self) -> str | None:
        return self._current

    def start(self, strategy: Strategy, tickers: list[str] | None = None, trigger: str = "manual") -> str:
        with self._lock:
            if self._current:
                raise ScanBusy(self._current)
            record = new_record(strategy)
            record["trigger"] = trigger
            scan_store.save(record)
            self._current = record["id"]

        def save(r: dict):
            r["trigger"] = trigger
            scan_store.save(r)

        def work():
            try:
                sources = self._sources_factory() if self._sources_factory else None
                run_scan(strategy, tickers, sources=sources, on_update=save, scan_id=record["id"])
            finally:
                with self._lock:
                    self._current = None

        threading.Thread(target=work, daemon=True, name=f"scan-{record['id']}").start()
        return record["id"]

    def run_blocking(self, strategy: Strategy, tickers: list[str] | None = None, sources: Sources | None = None, trigger: str = "manual") -> dict:
        def save(r: dict):
            r["trigger"] = trigger
            scan_store.save(r)
        return run_scan(strategy, tickers, sources=sources, on_update=save)


runner = ScanRunner()
