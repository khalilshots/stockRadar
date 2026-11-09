from datetime import date, datetime, timedelta

from config.settings import settings
from tools.http import SourceUnavailable, get_json

URL = "https://newsapi.org/v2/everything"


def get_news(ticker: str, company_name: str | None = None, days: int | None = None) -> list[dict]:
    """Headlines mentioning the ticker or company name, newest first."""
    days = days or settings.news_lookback_days
    start = date.today() - timedelta(days=days)
    query = f'"{ticker}"' if not company_name else f'"{ticker}" OR "{company_name}"'
    data = get_json(
        api="newsapi",
        url=URL,
        params={
            "q": query,
            "from": start.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": settings.newsapi_key,
        },
        cache_key=f"news:{query}:{start}",
        ttl=60 * 60,
        secret_param="apiKey",
    )
    if data.get("status") != "ok":
        raise SourceUnavailable(f"newsapi: {data.get('code', 'error')}")

    articles = []
    for item in data.get("articles", []):
        published = item.get("publishedAt")
        try:
            ts = int(datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp())
        except (AttributeError, ValueError):
            ts = None
        articles.append({
            "headline": item.get("title") or "",
            "summary": (item.get("description") or "")[:300],
            "source": (item.get("source") or {}).get("name", ""),
            "url": item.get("url", ""),
            "published": ts,
        })
    return [a for a in articles if a["headline"]]
