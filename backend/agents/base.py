def result(ticker: str, agent: str, passed: bool, reason: str, source: str = "rules", **data) -> dict:
    """The shape every agent returns, so one gate works after all of them."""
    return {"ticker": ticker, "agent": agent, "passed": passed, "reason": reason, "source": source, "data": data}


def missing(ticker: str, agent: str, reason: str) -> dict:
    return {"ticker": ticker, "agent": agent, "passed": False, "data_missing": True, "reason": reason, "source": "rules", "data": {}}


def fmt_int(n) -> str:
    return f"{int(n):,}" if n is not None else "n/a"
