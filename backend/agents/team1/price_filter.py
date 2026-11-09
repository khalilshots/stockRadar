from typing import Callable

from agents.base import fmt_int, missing, result
from strategies.strategy_manager import Criteria

AGENT = "price_filter"


def run(snap: dict, criteria: Criteria, get_fundamentals: Callable[[str], dict]) -> dict:
    """
    Price, gap, prior-day run and float. Plain comparisons, no LLM needed.
    The float lookup is a separate network call, so it only happens once the
    cheap price checks have passed.
    """
    ticker = snap["ticker"]
    price = snap.get("price")
    if price is None:
        return missing(ticker, AGENT, "no price")

    if not criteria.price_min <= price <= criteria.price_max:
        return result(ticker, AGENT, False, f"price ${price:.2f} is outside ${criteria.price_min:g}-${criteria.price_max:g}", price=price)

    gap = snap.get("gap_percent")
    if gap is None or gap < criteria.min_gap_percent:
        return result(ticker, AGENT, False, f"gap {gap}% is under the {criteria.min_gap_percent:g}% minimum", gap_percent=gap)

    prior = snap.get("prior_day_gain")
    if prior is not None and prior > criteria.max_prior_day_gain:
        return result(ticker, AGENT, False, f"already ran {prior}% yesterday, over the {criteria.max_prior_day_gain:g}% cap", prior_day_gain=prior)

    float_shares = None
    if criteria.max_float:
        float_shares = get_fundamentals(ticker).get("float_shares")
        if not float_shares:
            return missing(ticker, AGENT, "float not available")
        if float_shares > criteria.max_float:
            return result(ticker, AGENT, False, f"float {fmt_int(float_shares)} is over {fmt_int(criteria.max_float)}", float_shares=float_shares)

    reason = f"${price:.2f}, gapped {gap}%"
    if float_shares:
        reason += f", float {fmt_int(float_shares)}"
    return result(ticker, AGENT, True, reason, price=price, gap_percent=gap, float_shares=float_shares)
