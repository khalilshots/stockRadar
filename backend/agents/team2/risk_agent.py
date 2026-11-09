import math

from agents.base import missing, result

AGENT = "risk_agent"
STOP_ATR_MULTIPLE = 1.5
MAX_STOP_PERCENT = 20
REDUCED_SIZE_REGIMES = {"elevated", "high_volatility"}


def run(snap: dict, risk_per_trade: float, regime: dict | None = None) -> dict:
    """
    Turns a setup into a trade plan: stop 1.5 ATR under entry, size so that
    getting stopped out loses exactly risk_per_trade, targets at 2R and 3R.
    Pure math, so no LLM. Size gets cut in half when the VIX is elevated.
    """
    ticker = snap["ticker"]
    entry, atr = snap.get("price"), snap.get("atr_14")
    if not entry or not atr:
        return missing(ticker, AGENT, "no price or ATR")

    stop = round(entry - STOP_ATR_MULTIPLE * atr, 2)
    risk_per_share = round(entry - stop, 4)
    stop_percent = round(risk_per_share / entry * 100, 1)

    if stop <= 0 or stop_percent > MAX_STOP_PERCENT:
        return result(ticker, AGENT, False, f"stop would be {stop_percent}% away, too volatile to size", stop_percent=stop_percent)

    budget = risk_per_trade
    note = ""
    if regime and regime.get("regime") in REDUCED_SIZE_REGIMES:
        budget = risk_per_trade / 2
        note = f", size halved (VIX {regime.get('vix')})"

    shares = math.floor(budget / risk_per_share)
    if shares < 1:
        return result(ticker, AGENT, False, f"${budget:g} risk can't buy one share with a ${risk_per_share:.2f} stop")

    position_value = round(shares * entry, 2)
    avg_volume = snap.get("avg_volume_20") or 0
    liquidity_share = round(shares / avg_volume * 100, 2) if avg_volume else None

    plan = {
        "entry": round(entry, 2),
        "stop": stop,
        "stop_percent": stop_percent,
        "risk_per_share": round(risk_per_share, 2),
        "shares": shares,
        "position_value": position_value,
        "max_loss": round(shares * risk_per_share, 2),
        "target_1": round(entry + 2 * risk_per_share, 2),
        "target_2": round(entry + 3 * risk_per_share, 2),
        "percent_of_avg_volume": liquidity_share,
    }
    reason = f"{shares} shares at ${plan['entry']}, stop ${stop} ({stop_percent}%), targets ${plan['target_1']} / ${plan['target_2']}{note}"
    return result(ticker, AGENT, True, reason, **plan)
