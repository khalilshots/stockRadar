from agents.base import fmt_int, missing, result
from strategies.strategy_manager import Criteria

AGENT = "volume_agent"


def run(snap: dict, criteria: Criteria) -> dict:
    """Is anyone actually trading it? Raw volume plus volume against its 20-day average."""
    ticker = snap["ticker"]
    volume = snap.get("volume")
    rel = snap.get("relative_volume")
    if volume is None or rel is None:
        return missing(ticker, AGENT, "no volume history")

    if volume < criteria.min_volume:
        return result(ticker, AGENT, False, f"volume {fmt_int(volume)} is under {fmt_int(criteria.min_volume)}", volume=volume)

    if rel < criteria.min_relative_volume:
        return result(ticker, AGENT, False, f"relative volume {rel}x is under {criteria.min_relative_volume:g}x", relative_volume=rel)

    return result(ticker, AGENT, True, f"{fmt_int(volume)} shares, {rel}x normal", volume=volume, relative_volume=rel)
