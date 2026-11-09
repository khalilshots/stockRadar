from agents.team2.setup import above, grade

DESCRIPTION = "price trending above a rising 20-day average, RSI strong but not exhausted (55-85), up over the last week, volume above normal."


def run(snap: dict) -> dict:
    rsi = snap.get("rsi_14")
    sma50 = snap.get("sma_50")
    checks = {
        "above SMA20": above(snap.get("price"), snap.get("sma_20")),
        "SMA20 above SMA50": above(snap.get("sma_20"), sma50) if sma50 is not None else True,
        "RSI 55-85": rsi is not None and 55 <= rsi <= 85,
        "up 5%+ this week": (snap.get("change_5d") or 0) > 5,
        "volume 1.5x+": (snap.get("relative_volume") or 0) >= 1.5,
    }
    return grade(snap, "momentum", DESCRIPTION, checks, core=["above SMA20", "RSI 55-85"])
