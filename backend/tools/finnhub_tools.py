from datetime import date, timedelta

from config.settings import settings
from tools.http import get_json

BASE = "https://finnhub.io/api/v1"


def get_company_news(ticker: str, days: int | None = None) -> list[dict]:
    """Recent headlines for a ticker, newest first."""
    days = days or settings.news_lookback_days
    end = date.today()
    start = end - timedelta(days=days)
    data = get_json(
        api="finnhub",
        url=f"{BASE}/company-news",
        params={"symbol": ticker, "from": start.isoformat(), "to": end.isoformat(), "token": settings.finnhub_key},
        cache_key=f"news:{ticker}:{start}:{end}",
        ttl=30 * 60,
        secret_param="token",
    )
    articles = [
        {
            "headline": item.get("headline", ""),
            "summary": (item.get("summary") or "")[:300],
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published": item.get("datetime"),
        }
        for item in data or []
        if item.get("headline")
    ]
    return sorted(articles, key=lambda a: a["published"] or 0, reverse=True)


def get_quote(ticker: str) -> dict:
    data = get_json(
        api="finnhub",
        url=f"{BASE}/quote",
        params={"symbol": ticker, "token": settings.finnhub_key},
        cache_key=f"quote:{ticker}",
        ttl=60,
        secret_param="token",
    )
    return {
        "price": data.get("c"),
        "change_percent": data.get("dp"),
        "prev_close": data.get("pc"),
        "open": data.get("o"),
        "high": data.get("h"),
        "low": data.get("l"),
    }
