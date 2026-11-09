import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from agents.team1 import catalyst_agent, price_filter, volume_agent
from agents.team2 import breakout_agent, momentum_agent, reversal_agent, risk_agent, scoring_agent
from config.settings import settings
from strategies.strategy_manager import Strategy
from tools import alphavantage_tools, finnhub_tools, fred_tools, newsapi_tools
from tools.http import SourceUnavailable
from tools.yfinance_tools import YahooData
from utils import llm
from utils.gates import check_gate
from utils.indicators import snapshot

logger = logging.getLogger(__name__)


@dataclass
class Sources:
    """Where the pipeline gets its data. Tests pass in fakes."""
    market: object
    news: Callable[[str, str | None], list[dict]] | None = None
    sentiment: Callable[[str], dict] | None = None
    regime: Callable[[], dict] | None = None


def default_sources() -> Sources:
    fetchers = []
    if settings.finnhub_key:
        fetchers.append(lambda ticker, company: finnhub_tools.get_company_news(ticker))
    if settings.newsapi_key:
        fetchers.append(lambda ticker, company: newsapi_tools.get_news(ticker, company))

    def get_news(ticker: str, company: str | None) -> list[dict]:
        # finnhub first, newsapi as backup
        error = None
        for fetch in fetchers:
            try:
                return fetch(ticker, company)
            except SourceUnavailable as e:
                error = e
        raise error

    return Sources(
        market=YahooData(),
        news=get_news if fetchers else None,
        sentiment=alphavantage_tools.get_news_sentiment if settings.alpha_vantage_key else None,
        regime=fred_tools.market_regime if settings.fred_key else None,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_record(strategy: Strategy, scan_id: str | None = None) -> dict:
    return {
        "id": scan_id or datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2),
        "strategy": strategy.name,
        "criteria": strategy.model_dump(),
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "progress": {"stage": "starting", "done": 0, "total": 0},
        "llm": {"model": settings.llm_model if settings.llm_enabled else None, "used": False},
        "sources": settings.sources(),
        "regime": None,
        "counts": {"universe": 0, "with_data": 0, "watchlist": 0, "analysis_passed": 0, "final": 0},
        "final": [],
        "watchlist": [],
        "dropped": [],
        "traces": {},
        "snapshots": {},
        "error": None,
    }


def run_scan(strategy: Strategy, tickers: list[str] | None = None, sources: Sources | None = None,
             on_update: Callable[[dict], None] | None = None, scan_id: str | None = None) -> dict:
    """
    Universe -> Discovery team -> watchlist -> Analysis team -> ranked final list.
    Every agent result goes through the same gate, and every drop is recorded
    with the agent and reason so the dashboard can show why a ticker fell out.
    """
    sources = sources or default_sources()
    record = new_record(strategy, scan_id)
    llm.reset()
    last_push = 0.0

    def push(force: bool = False):
        nonlocal last_push
        if on_update and (force or time.time() - last_push > 1):
            last_push = time.time()
            on_update(record)

    def stage(name: str, total: int = 0):
        record["progress"] = {"stage": name, "done": 0, "total": total}
        push(force=True)

    def drop(ticker: str, stage_name: str, res: dict):
        record["dropped"].append({"ticker": ticker, "stage": stage_name, "agent": res["agent"], "reason": res["reason"]})

    def used_llm(res: dict):
        if res.get("source") == "llm":
            record["llm"]["used"] = True

    try:
        # 1. universe
        stage("universe")
        if tickers:
            universe = list(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))
        else:
            universe = sources.market.universe(strategy.universe, settings.max_universe_size)
        record["counts"]["universe"] = len(universe)

        # 2. price history and indicators, one batch call
        stage("market data", len(universe))
        frames = sources.market.history(universe)
        snaps = {t: snapshot(t, frames[t]) for t in universe if t in frames}
        for t in universe:
            if t not in snaps:
                drop(t, "data", {"agent": "market_data", "reason": "no price history"})
        record["counts"]["with_data"] = len(snaps)

        if sources.regime:
            try:
                record["regime"] = sources.regime()
            except SourceUnavailable as e:
                logger.info(f"no market regime: {e}")

        # 3. discovery team: price/float -> volume -> catalyst, cheapest first
        stage("discovery", len(snaps))
        fundamentals: dict[str, dict] = {}

        def get_fundamentals(ticker: str) -> dict:
            if ticker not in fundamentals:
                fundamentals[ticker] = sources.market.fundamentals(ticker) or {}
            return fundamentals[ticker]

        survivors = []
        for i, (ticker, snap) in enumerate(snaps.items(), 1):
            trace = record["traces"].setdefault(ticker, [])
            steps = [
                lambda s=snap: price_filter.run(s, strategy.criteria, get_fundamentals),
                lambda s=snap: volume_agent.run(s, strategy.criteria),
                lambda s=snap, t=ticker: catalyst_agent.run(s, strategy.criteria, sources.news, fundamentals.get(t, {}).get("name")),
            ]
            for step in steps:
                res = step()
                trace.append(res)
                used_llm(res)
                if not check_gate(res):
                    drop(ticker, "discovery", res)
                    break
            else:
                survivors.append(ticker)
            record["progress"]["done"] = i
            push()

        survivors.sort(key=lambda t: snaps[t].get("relative_volume") or 0, reverse=True)
        for ticker in survivors[settings.max_watchlist_size:]:
            drop(ticker, "discovery", {"agent": "watchlist", "reason": f"outside the top {settings.max_watchlist_size} by relative volume"})
        watchlist = survivors[: settings.max_watchlist_size]
        record["counts"]["watchlist"] = len(watchlist)

        catalysts = {t: record["traces"][t][-1] for t in watchlist}
        for t in watchlist:
            info = get_fundamentals(t)
            record["snapshots"][t] = snaps[t]
            record["watchlist"].append({
                "ticker": t,
                "name": info.get("name") or t,
                "price": snaps[t]["price"],
                "change_percent": snaps[t]["change_percent"],
                "relative_volume": snaps[t]["relative_volume"],
                "catalyst": catalysts[t]["data"].get("headline"),
            })

        # 4. analysis team: setups -> setup gate -> risk
        stage("analysis", len(watchlist))
        prefs = [p.lower() for p in strategy.setup_preferences]
        candidates = []
        for i, ticker in enumerate(watchlist, 1):
            snap, trace = snaps[ticker], record["traces"][ticker]
            setups = [momentum_agent.run(snap), breakout_agent.run(snap), reversal_agent.run(snap)]
            for res in setups:
                trace.append(res)
                used_llm(res)

            usable = [s for s in setups if s["passed"] and (not prefs or s["data"]["setup"] in prefs)]
            if not usable:
                wanted = ", ".join(prefs) if prefs else "any"
                gate = {"ticker": ticker, "agent": "setup_gate", "passed": False, "source": "rules", "data": {},
                        "reason": f"no {wanted} setup"}
                trace.append(gate)
                drop(ticker, "analysis", gate)
                record["progress"]["done"] = i
                push()
                continue
            best = max(usable, key=lambda s: s["data"]["score"])

            risk = risk_agent.run(snap, strategy.risk_per_trade, record["regime"])
            trace.append(risk)
            if not check_gate(risk):
                drop(ticker, "analysis", risk)
            else:
                candidates.append({"ticker": ticker, "setup": best, "setups": setups, "catalyst": catalysts[ticker], "risk": risk})
            record["progress"]["done"] = i
            push()
        record["counts"]["analysis_passed"] = len(candidates)

        # 5. scoring: rough rank, sentiment for the top few (alpha vantage is 25 calls a day), final rank
        stage("scoring", len(candidates))
        candidates.sort(key=lambda c: scoring_agent.score(c["setup"], c["catalyst"], snaps[c["ticker"]], None)[0], reverse=True)
        sentiment: dict[str, dict] = {}
        if sources.sentiment:
            for c in candidates[: settings.alpha_vantage_per_scan]:
                try:
                    sentiment[c["ticker"]] = sources.sentiment(c["ticker"])
                except SourceUnavailable as e:
                    logger.info(f"sentiment skipped: {e}")
                    break

        for c in candidates:
            c["score"] = scoring_agent.score(c["setup"], c["catalyst"], snaps[c["ticker"]], sentiment.get(c["ticker"]))[0]
        candidates.sort(key=lambda c: c["score"], reverse=True)

        for rank, c in enumerate(candidates, 1):
            ticker = c["ticker"]
            in_final = rank <= settings.max_final_list_size
            scored = scoring_agent.run(snaps[ticker], c["setup"], c["catalyst"], c["risk"], sentiment.get(ticker), write_note=in_final)
            record["traces"][ticker].append(scored)
            used_llm(scored)
            if not in_final:
                drop(ticker, "ranking", {"agent": "scoring_agent", "reason": f"score {scored['data']['score']}, ranked {rank}, outside the top {settings.max_final_list_size}"})
                continue
            record["final"].append(_candidate(ticker, snaps[ticker], get_fundamentals(ticker),
                                              c, scored, sentiment.get(ticker)))
            record["progress"]["done"] = rank
            push()
        record["counts"]["final"] = len(record["final"])
        record["status"] = "done"
        record["progress"]["stage"] = "done"

    except Exception as e:
        logger.exception("scan failed")
        record["status"] = "failed"
        record["error"] = f"{type(e).__name__}: {e}"

    record["finished_at"] = _now()
    push(force=True)
    return record


def _candidate(ticker: str, snap: dict, info: dict, c: dict, scored: dict, sentiment: dict | None) -> dict:
    cat = c["catalyst"]["data"]
    return {
        "ticker": ticker,
        "name": info.get("name") or ticker,
        "sector": info.get("sector"),
        "float_shares": info.get("float_shares"),
        "price": snap["price"],
        "change_percent": snap["change_percent"],
        "gap_percent": snap["gap_percent"],
        "relative_volume": snap["relative_volume"],
        "setup": c["setup"]["data"]["setup"],
        "setup_score": c["setup"]["data"]["score"],
        "setups": {s["data"]["setup"]: {"present": s["passed"], "score": s["data"]["score"]} for s in c["setups"]},
        "score": scored["data"]["score"],
        "breakdown": scored["data"]["breakdown"],
        "summary": scored["data"]["summary"],
        "catalyst": {
            "type": cat.get("catalyst_type"),
            "sentiment": cat.get("sentiment"),
            "headline": cat.get("headline"),
            "url": cat.get("url"),
            "source": c["catalyst"]["source"],
        },
        "news_sentiment": sentiment,
        "plan": c["risk"]["data"],
    }
