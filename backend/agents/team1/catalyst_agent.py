import re
from typing import Callable, Literal

from pydantic import BaseModel, Field

from agents.base import missing, result
from strategies.strategy_manager import Criteria
from tools.http import SourceUnavailable
from utils import llm

AGENT = "catalyst_agent"

NEGATIVE = r"offering|dilut|priced .* shares|reverse split|bankrupt|delist|going concern|downgrade|lawsuit|investigation|misses|cuts guidance|halt"
POSITIVE = {
    "fda": r"\bfda\b|approval|approved|clinical|phase [123]|trial results",
    "earnings": r"earnings|revenue|beats|guidance|quarter|q[1-4]\b",
    "contract": r"contract|award|order|deal with|agreement|partnership|partners with",
    "m&a": r"acquire|acquisition|merger|buyout|takeover",
    "analyst": r"upgrade|price target|initiates coverage",
    "product": r"launch|unveil|patent|breakthrough",
}

SYSTEM = """You review stock news headlines for a momentum trader.
Decide if there is a real catalyst explaining today's move.
Reply with only this JSON:
{"has_catalyst": true or false,
 "catalyst_type": "fda" | "earnings" | "contract" | "m&a" | "analyst" | "product" | "offering" | "other" | "none",
 "sentiment": "positive" | "negative" | "neutral",
 "strength": 0-100,
 "headline": "the headline that matters most, copied exactly",
 "reason": "one short sentence"}
Share offerings, dilution, reverse splits and lawsuits are negative catalysts."""


class CatalystVerdict(BaseModel):
    has_catalyst: bool
    catalyst_type: str = "other"
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    strength: int = Field(default=50, ge=0, le=100)
    headline: str = ""
    reason: str = ""


def run(snap: dict, criteria: Criteria, get_news: Callable[[str, str | None], list[dict]] | None, company: str | None = None) -> dict:
    ticker = snap["ticker"]

    if get_news is None:
        return result(ticker, AGENT, True, "skipped, no news api key set", source="skipped", catalyst_type=None, strength=None)

    try:
        articles = get_news(ticker, company)
    except SourceUnavailable as e:
        if criteria.require_catalyst:
            return missing(ticker, AGENT, f"news unavailable ({e})")
        return result(ticker, AGENT, True, f"news unavailable ({e}), not required", source="skipped", catalyst_type=None, strength=None)

    if not articles:
        if criteria.require_catalyst:
            return result(ticker, AGENT, False, "no news in the lookback window", catalyst_type="none", strength=0)
        return result(ticker, AGENT, True, "no news, catalyst not required", catalyst_type="none", strength=0)

    articles = articles[:8]
    verdict, source = _ask_llm(ticker, snap, articles), "llm"
    if verdict is None:
        verdict, source = _rules(articles), "rules"

    headline = verdict.headline or articles[0]["headline"]
    data = {
        "catalyst_type": verdict.catalyst_type,
        "sentiment": verdict.sentiment,
        "strength": verdict.strength,
        "headline": headline,
        "url": next((a["url"] for a in articles if a["headline"] == headline), articles[0]["url"]),
        "articles": len(articles),
    }

    if verdict.sentiment == "negative":
        return result(ticker, AGENT, False, f"negative catalyst: {verdict.reason or headline}", source, **data)
    if not verdict.has_catalyst and criteria.require_catalyst:
        return result(ticker, AGENT, False, f"no real catalyst: {verdict.reason or 'headlines are noise'}", source, **data)
    return result(ticker, AGENT, True, verdict.reason or headline, source, **data)


def _ask_llm(ticker: str, snap: dict, articles: list[dict]) -> CatalystVerdict | None:
    lines = "\n".join(f"- {a['headline']} ({a['source']})" for a in articles)
    user = f"{ticker} is up {snap.get('change_percent')}% today on {snap.get('relative_volume')}x normal volume.\n\nHeadlines:\n{lines}"
    return llm.ask(SYSTEM, user, CatalystVerdict)


def _rules(articles: list[dict]) -> CatalystVerdict:
    """Keyword fallback when the model isn't available."""
    for article in articles:
        text = f"{article['headline']} {article['summary']}".lower()
        if re.search(NEGATIVE, text):
            return CatalystVerdict(has_catalyst=True, catalyst_type="offering", sentiment="negative", strength=70,
                                   headline=article["headline"], reason=article["headline"])
    for article in articles:
        text = f"{article['headline']} {article['summary']}".lower()
        for kind, pattern in POSITIVE.items():
            if re.search(pattern, text):
                return CatalystVerdict(has_catalyst=True, catalyst_type=kind, sentiment="positive", strength=60,
                                       headline=article["headline"], reason=f"{kind.upper() if len(kind) <= 3 else kind.capitalize()} news: {article['headline']}")
    return CatalystVerdict(has_catalyst=False, catalyst_type="none", sentiment="neutral", strength=20,
                           headline=articles[0]["headline"], reason="headlines don't explain the move")
