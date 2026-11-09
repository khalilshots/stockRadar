from agents.team2.setup import above, grade

DESCRIPTION = "close above the prior 20-day high on heavy volume, closing near the high of the day, not already stretched far past the breakout level."


def run(snap: dict) -> dict:
    price, high, low = snap.get("price"), snap.get("high"), snap.get("low")
    day_range = (high - low) if high is not None and low is not None else 0
    close_position = (price - low) / day_range if day_range else 0
    extension = snap.get("pct_from_high_20")
    sma50 = snap.get("sma_50")
    checks = {
        "above 20d high": above(price, snap.get("high_20")),
        "volume 1.5x+": (snap.get("relative_volume") or 0) >= 1.5,
        "closed near high": close_position >= 0.75,
        "within 10% of breakout": extension is not None and extension <= 10,
        "above SMA50": above(price, sma50) if sma50 is not None else True,
    }
    return grade(snap, "breakout", DESCRIPTION, checks, core=["above 20d high", "volume 1.5x+"])
