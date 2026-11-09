from config.settings import settings
from tools.http import SourceUnavailable, get_json

URL = "https://www.alphavantage.co/query"


def get_news_sentiment(ticker: str) -> dict:
    """
    Average news sentiment for a ticker from Alpha Vantage.
    Score runs from -1 (bearish) to 1 (bullish). Free tier is 25 calls a day,
    so this only runs on the final candidates.
    """
    data = get_json(
        api="alpha_vantage",
        url=URL,
        params={"function": "NEWS_SENTIMENT", "tickers": ticker, "limit": 50, "apikey": settings.alpha_vantage_key},
        cache_key=f"sentiment:{ticker}",
        ttl=6 * 60 * 60,
        secret_param="apikey",
    )
    # alpha vantage returns 200 with a note when you're throttled
    if "feed" not in data:
        raise SourceUnavailable("alpha_vantage: " + (data.get("Information") or data.get("Note") or "no feed")[:80])

    scores = []
    for article in data["feed"]:
        for ts in article.get("ticker_sentiment", []):
            if ts.get("ticker") == ticker and float(ts.get("relevance_score", 0)) >= 0.3:
                scores.append(float(ts["ticker_sentiment_score"]))

    if not scores:
        return {"score": 0.0, "label": "Neutral", "articles": 0}

    avg = sum(scores) / len(scores)
    return {"score": round(avg, 3), "label": _label(avg), "articles": len(scores)}


def _label(score: float) -> str:
    # alpha vantage's own buckets
    if score <= -0.35:
        return "Bearish"
    if score <= -0.15:
        return "Somewhat-Bearish"
    if score < 0.15:
        return "Neutral"
    if score < 0.35:
        return "Somewhat-Bullish"
    return "Bullish"
