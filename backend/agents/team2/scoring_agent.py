from pydantic import BaseModel

from agents.base import result
from utils import llm

AGENT = "scoring_agent"
WEIGHTS = {"setup": 0.5, "catalyst": 0.2, "volume": 0.15, "sentiment": 0.15}

SYSTEM = """You write one-line trade notes for a momentum trader.
Given the facts, write two short sentences: why this stock is on the list and what would invalidate it.
Use the numbers given. No hype, no advice language.
Reply with only this JSON: {"summary": "..."}"""


class Note(BaseModel):
    summary: str


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

    facts = (
        f"{ticker}: {setup['data']['setup']} setup scored {parts['setup']} ({setup['reason']}). "
        f"Catalyst: {catalyst['reason']}. Relative volume {snap.get('relative_volume')}x, up {snap.get('change_percent')}% today. "
        f"Plan: entry ${plan['entry']}, stop ${plan['stop']}, target ${plan['target_1']}."
    )
    note = llm.ask(SYSTEM, facts, Note) if write_note else None
    if note and note.summary.strip():
        summary, source = note.summary.strip(), "llm"
    else:
        headline = catalyst["data"].get("headline")
        news = f'news: "{headline}"' if headline else "no catalyst checked"
        summary = (
            f"{setup['data']['setup'].capitalize()} setup on {snap.get('relative_volume')}x volume, {news}. "
            f"Invalid below ${plan['stop']}."
        )
        source = "rules"

    return result(ticker, AGENT, True, f"score {total}", source, score=total, breakdown=parts, summary=summary)
