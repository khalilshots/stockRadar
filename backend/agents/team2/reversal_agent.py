from agents.team2.setup import above, grade

DESCRIPTION = "a stock that sold off hard (oversold RSI or several red days, well below its 20-day high) and is turning up today on decent volume without breaking its 20-day low."


def run(snap: dict) -> dict:
    rsi = snap.get("rsi_14")
    from_high = snap.get("pct_from_high_20")
    checks = {
        "oversold": (rsi is not None and rsi < 40) or snap.get("down_streak", 0) >= 3,
        "15%+ off 20d high": from_high is not None and from_high <= -15,
        "green today": (snap.get("change_percent") or 0) > 0,
        "volume 1x+": (snap.get("relative_volume") or 0) >= 1.0,
        "holding 20d low": above(snap.get("price"), snap.get("low_20")),
    }
    return grade(snap, "reversal", DESCRIPTION, checks, core=["oversold", "15%+ off 20d high", "green today"])
