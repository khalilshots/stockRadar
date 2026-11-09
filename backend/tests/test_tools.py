import pandas as pd
import pytest
import yfinance as yf

from config.settings import settings
from tests.helpers import bars
from tools import alphavantage_tools, finnhub_tools, fred_tools, newsapi_tools
from tools.http import SourceUnavailable
from tools.yfinance_tools import YahooData
from utils import rate_limiter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.fixture
def http(monkeypatch):
    """Record requests and answer with whatever the test queues up."""
    calls, replies = [], []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params))
        return FakeResponse(replies.pop(0))

    monkeypatch.setattr("tools.http.requests.get", fake_get)
    return calls, replies


def test_history_splits_a_multi_ticker_download(monkeypatch):
    a, b = bars([5.0] * 30), bars([7.0] * 30)
    combined = pd.concat({"AAA": a, "BBB": b}, axis=1)
    monkeypatch.setattr(yf, "download", lambda *args, **kw: combined)
    frames = YahooData().history(["AAA", "BBB", "MISSING"])
    assert set(frames) == {"AAA", "BBB"}
    assert frames["BBB"]["Close"].iloc[-1] == 7.0


def test_universe_keeps_plain_us_symbols(monkeypatch):
    monkeypatch.setattr(yf, "screen", lambda q, count: {"quotes": [{"symbol": s} for s in ["SOFI", "BRK-B", "SHOP.TO", "^VIX", "SOFI"]]})
    assert YahooData().universe(["day_gainers"], 10) == ["SOFI", "BRK-B"]


def test_fundamentals_are_cached(monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, t):
            calls.append(t)
            self.info = {"shortName": "Acme", "floatShares": 4_000_000}

    monkeypatch.setattr(yf, "Ticker", FakeTicker)
    assert YahooData().fundamentals("ACME")["float_shares"] == 4_000_000
    assert YahooData().fundamentals("ACME")["name"] == "Acme"
    assert calls == ["ACME"]


def test_no_key_means_no_request(http):
    calls, _ = http
    with pytest.raises(SourceUnavailable):
        finnhub_tools.get_company_news("ACME")
    assert calls == []


def test_finnhub_news(http, monkeypatch):
    calls, replies = http
    monkeypatch.setattr(settings, "finnhub_key", "k")
    replies.append([
        {"headline": "older", "datetime": 100, "source": "x", "url": "u1", "summary": ""},
        {"headline": "newer", "datetime": 200, "source": "x", "url": "u2", "summary": ""},
        {"headline": "", "datetime": 300},
    ])
    news = finnhub_tools.get_company_news("ACME")
    assert [n["headline"] for n in news] == ["newer", "older"]
    # second call comes from the cache
    finnhub_tools.get_company_news("ACME")
    assert len(calls) == 1


def test_newsapi_error_status(http, monkeypatch):
    _, replies = http
    monkeypatch.setattr(settings, "newsapi_key", "k")
    replies.append({"status": "error", "code": "rateLimited"})
    with pytest.raises(SourceUnavailable):
        newsapi_tools.get_news("ACME")


def test_alpha_vantage_sentiment(http, monkeypatch):
    _, replies = http
    monkeypatch.setattr(settings, "alpha_vantage_key", "k")
    replies.append({"feed": [
        {"ticker_sentiment": [{"ticker": "ACME", "relevance_score": "0.9", "ticker_sentiment_score": "0.4"}]},
        {"ticker_sentiment": [{"ticker": "ACME", "relevance_score": "0.5", "ticker_sentiment_score": "0.2"}]},
        {"ticker_sentiment": [{"ticker": "ACME", "relevance_score": "0.1", "ticker_sentiment_score": "-0.9"}]},
    ]})
    s = alphavantage_tools.get_news_sentiment("ACME")
    assert s == {"score": 0.3, "label": "Somewhat-Bullish", "articles": 2}


def test_alpha_vantage_throttle_note(http, monkeypatch):
    _, replies = http
    monkeypatch.setattr(settings, "alpha_vantage_key", "k")
    replies.append({"Information": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."})
    with pytest.raises(SourceUnavailable):
        alphavantage_tools.get_news_sentiment("ACME")


def test_fred_regime_skips_blank_values(http, monkeypatch):
    _, replies = http
    monkeypatch.setattr(settings, "fred_key", "k")
    replies.append({"observations": [{"date": "2026-11-06", "value": "."}, {"date": "2026-11-05", "value": "26.4"}]})
    assert fred_tools.market_regime() == {"vix": 26.4, "as_of": "2026-11-05", "regime": "elevated"}


def test_daily_budget_runs_out(monkeypatch):
    monkeypatch.setattr(settings, "alpha_vantage_daily_limit", 2)
    assert rate_limiter.acquire("alpha_vantage")
    assert rate_limiter.acquire("alpha_vantage")
    assert not rate_limiter.acquire("alpha_vantage")
    assert rate_limiter.remaining("alpha_vantage") == 0
