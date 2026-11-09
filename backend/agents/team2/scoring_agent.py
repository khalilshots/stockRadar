from pydantic import BaseModel

from agents.base import result
from utils import llm

AGENT = "scoring_agent"
WEIGHTS = {"setup": 0.5, "catalyst": 0.2, "volume": 0.15, "sentiment": 0.15}

SYSTEM = """You write scan notes for a trader. In one sentence, say why this stock showed up today.
Use only the facts given and name one or two of the numbers (today's move, relative volume, RSI,
distance from the 20-day high, the news headline).
Don't predict prices, don't mention scores or probabilities, don't give advice, don't mention stops.
Reply with only this JSON: {"why": "..."}"""


class Note(BaseModel):
    why: str


def score(setup: dict, catalyst: dict, snap: dict, sentiment: dict | None) -> tuple[int, dict]:
    """Weighted 0-100 score. Missing pieces count as neutral (50) instead of zero."""
    parts = {
        "setup": setup["data"].get("score", 0),
        "catalyst": catalyst["data"].get("strength") if catalyst["data"].get("strength") is not None else 50,
        "volume": min((snap.get("relative_volume") or 0) / 5, 1) * 100,
        "sentiment": (sentiment["score"] + 1) / 2 * 100 if sentiment else 50,
    }
    total = sum(parts[k] * w for k, w in WEIGHTS.items())
    return round(total), {k: round(v) for k, v in parts.items()}


def run(snap: dict, setup: dict, catalyst: dict, risk: dict, sentiment: dict | None = None, write_note: bool = True) -> dict:
    ticker = snap["ticker"]
    total, parts = score(setup, catalyst, snap, sentiment)
    plan = risk["data"]

    headline = catalyst["data"].get("headline")
    facts = "\n".join(f"{k}: {v}" for k, v in {
        "ticker": ticker,
        "setup": setup["data"]["setup"],
        "setup checks passed": ", ".join(k for k, ok in setup["data"].get("checks", {}).items() if ok),
        "change today %": snap.get("change_percent"),
        "relative volume": f"{snap.get('relative_volume')}x",
        "RSI": snap.get("rsi_14"),
        "% from 20-day high": snap.get("pct_from_high_20"),
        "red days in a row before today": snap.get("down_streak") or None,
        "news": headline,
    }.items() if v not in (None, ""))

    # the model writes the "why", the invalidation level comes from the risk agent so it can't be wrong
    note = llm.ask(SYSTEM, facts, Note) if write_note else None
    if note and note.why.strip():
        why, source = note.why.strip().rstrip(".") + ".", "llm"
    else:
        news = f'news: "{headline}"' if headline else "no catalyst checked"
        why, source = f"{setup['data']['setup'].capitalize()} setup on {snap.get('relative_volume')}x volume, {news}.", "rules"
    summary = f"{why} Invalid below ${plan['stop']}."

    return result(ticker, AGENT, True, f"score {total}", source, score=total, breakdown=parts, summary=summary)
