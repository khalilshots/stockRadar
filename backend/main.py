import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import scheduler
from config.settings import settings
from scan_runner import ScanBusy, runner
from strategies import strategy_manager
from strategies.strategy_manager import Strategy
from utils import rate_limiter, scan_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
SCAN_ID = re.compile(r"^[\w-]{1,40}$")
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    if settings.scheduler_enabled:
        _scheduler = scheduler.start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="Stock Radar API", lifespan=lifespan)

# the vite dev server proxies /api, this covers running the frontend on its own
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    strategy: str
    tickers: list[str] | None = Field(default=None, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return {
        "llm_model": settings.llm_model if settings.llm_enabled else None,
        "sources": settings.sources(),
        "remaining_today": {api: rate_limiter.remaining(api) for api in ("alpha_vantage", "newsapi", "fred")},
        "scan_running": runner.current,
        "scheduler": {"enabled": settings.scheduler_enabled, "next_runs": scheduler.next_runs(_scheduler)},
    }


@app.get("/api/strategies")
def list_strategies() -> list[Strategy]:
    return strategy_manager.load_all()


@app.put("/api/strategies")
def upsert_strategy(strategy: Strategy) -> Strategy:
    return strategy_manager.save_strategy(strategy)


@app.delete("/api/strategies/{name}")
def delete_strategy(name: str):
    if not strategy_manager.delete_strategy(name):
        raise HTTPException(404, f"no strategy named {name!r}")
    return {"deleted": name}


@app.post("/api/scans", status_code=202)
def start_scan(req: ScanRequest):
    strategy = strategy_manager.get_strategy(req.strategy)
    if not strategy:
        raise HTTPException(404, f"no strategy named {req.strategy!r}")
    try:
        scan_id = runner.start(strategy, req.tickers)
    except ScanBusy as busy:
        raise HTTPException(409, f"scan {busy} is still running")
    return {"id": scan_id}


@app.get("/api/scans")
def list_scans(limit: int = 20):
    return scan_store.recent(min(limit, 100))


@app.get("/api/scans/latest")
def latest_scan():
    scan = scan_store.latest()
    if not scan:
        raise HTTPException(404, "no scans yet")
    return scan


def _load(scan_id: str) -> dict:
    scan = scan_store.get(scan_id) if SCAN_ID.match(scan_id) else None
    if not scan:
        raise HTTPException(404, "scan not found")
    return scan


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str):
    return _load(scan_id)


@app.get("/api/scans/{scan_id}/tickers/{ticker}")
def get_ticker(scan_id: str, ticker: str):
    scan = _load(scan_id)
    ticker = ticker.upper()
    trace = scan["traces"].get(ticker)
    if trace is None:
        raise HTTPException(404, f"{ticker} wasn't in this scan")
    return {
        "ticker": ticker,
        "trace": trace,
        "snapshot": scan["snapshots"].get(ticker),
        "candidate": next((c for c in scan["final"] if c["ticker"] == ticker), None),
        "dropped": next((d for d in scan["dropped"] if d["ticker"] == ticker), None),
    }
