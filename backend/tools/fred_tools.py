from config.settings import settings
from tools.http import SourceUnavailable, get_json

URL = "https://api.stlouisfed.org/fred/series/observations"


def latest_value(series_id: str) -> tuple[str, float]:
    """Most recent non-empty observation for a FRED series, as (date, value)."""
    data = get_json(
        api="fred",
        url=URL,
        params={"series_id": series_id, "file_type": "json", "sort_order": "desc", "limit": 10, "api_key": settings.fred_key},
        cache_key=f"series:{series_id}",
        ttl=6 * 60 * 60,
        secret_param="api_key",
    )
    for obs in data.get("observations", []):
        if obs.get("value") not in (None, "", "."):
            return obs["date"], float(obs["value"])
    raise SourceUnavailable(f"fred: no data for {series_id}")


def market_regime() -> dict:
    """
    VIX level as a simple risk-on / risk-off read.
    Above 25 the risk agent cuts position size in half.
    """
    as_of, vix = latest_value("VIXCLS")
    if vix >= 30:
        regime = "high_volatility"
    elif vix >= 25:
        regime = "elevated"
    else:
        regime = "normal"
    return {"vix": vix, "as_of": as_of, "regime": regime}
