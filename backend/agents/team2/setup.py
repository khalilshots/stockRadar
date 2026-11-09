from pydantic import BaseModel, Field

from agents.base import result
from utils import llm

SYSTEM = """You are a technical analyst grading a {setup} setup on a daily chart.
What a good {setup} looks like: {description}
The stock already meets the basic {setup} conditions. Judge how clean it is.
Reply with only this JSON:
{{"present": true or false, "score": 0-100, "reason": "one short sentence citing the numbers"}}
Use present=false only if the numbers clearly show a bad {setup}."""

FACT_KEYS = [
    "price", "change_percent", "gap_percent", "relative_volume", "rsi_14", "atr_14",
    "sma_20", "sma_50", "high_20", "low_20", "pct_from_high_20", "change_5d", "down_streak",
    "high", "low",
]


class SetupVerdict(BaseModel):
    present: bool
    score: int = Field(ge=0, le=100)
    reason: str = ""


def grade(snap: dict, setup: str, description: str, checks: dict[str, bool], core: list[str]) -> dict:
    """
    Shared logic for the three setup agents.
    The rules decide if the setup exists at all, so the model can't call a
    breakout on a stock that's below its 20-day high. If it does exist, the
    model grades how good it is. Without a model, the rule score stands.
    """
    ticker = snap["ticker"]
    agent = f"{setup}_agent"
    met = [name for name, ok in checks.items() if ok]
    rule_score = round(100 * len(met) / len(checks))
    failed_core = [name for name in core if not checks.get(name)]

    if failed_core:
        reason = f"no {setup}: " + ", ".join(failed_core) + " not met"
        return result(ticker, agent, False, reason, setup=setup, score=rule_score, checks=checks)

    facts = "\n".join(f"{k}: {snap.get(k)}" for k in FACT_KEYS if snap.get(k) is not None)
    user = f"Ticker: {ticker}\n{facts}\n\nRule checks passed: {', '.join(met)}"
    verdict = llm.ask(SYSTEM.format(setup=setup, description=description), user, SetupVerdict)

    if verdict is None:
        reason = f"{setup} setup, {len(met)}/{len(checks)} checks: " + ", ".join(met)
        return result(ticker, agent, True, reason, "rules", setup=setup, score=rule_score, checks=checks)

    return result(ticker, agent, verdict.present, verdict.reason or f"{setup} graded {verdict.score}", "llm",
                  setup=setup, score=verdict.score if verdict.present else min(verdict.score, 30), checks=checks)


def above(a, b) -> bool:
    return a is not None and b is not None and a > b
