import logging
import re

import pandas as pd
import yfinance as yf

from config.settings import settings
from utils import cache

logger = logging.getLogger(__name__)

US_SYMBOL = re.compile(r"^[A-Z]{1,5}(-[A-Z])?$")


class YahooData:
    """Market data from Yahoo Finance. The orchestrator only talks to this interface,
    so tests can swap in fake data."""

    def universe(self, screens: list[str], limit: int) -> list[str]:
        """Tickers from Yahoo's predefined screens (day_gainers, small_cap_gainers, ...)."""
        tickers: list[str] = []
        for screen in screens:
            try:
                result = yf.screen(screen, count=250)
            except Exception as e:
                logger.warning(f"screen {screen} failed: {e}")
                continue
            for quote in result.get("quotes", []):
                symbol = quote.get("symbol", "")
                if US_SYMBOL.match(symbol) and symbol not in tickers:
                    tickers.append(symbol)
        return tickers[:limit]

    def history(self, tickers: list[str], period: str | None = None) -> dict[str, pd.DataFrame]:
        """Daily OHLCV for each ticker. During market hours the last row is today so far."""
        if not tickers:
            return {}
        raw = yf.download(
            tickers,
            period=period or settings.history_period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw is None or raw.empty:
            return {}

        frames = {}
        for ticker in tickers:
            try:
                df = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                continue
            df = df.dropna(subset=["Close"])
            if len(df) >= 2:
                frames[ticker] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        return frames

    def fundamentals(self, ticker: str) -> dict:
        """Float, name and sector. Cached for 12 hours since these barely move."""
        cached = cache.read("yfinance", f"info:{ticker}", ttl=12 * 60 * 60)
        if cached is not None:
            return cached
        try:
            info = yf.Ticker(ticker).info
        except Exception as e:
            logger.warning(f"info for {ticker} failed: {e}")
            return {}
        data = {
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange"),
            "market_cap": info.get("marketCap"),
            "float_shares": info.get("floatShares"),
            "shares_outstanding": info.get("sharesOutstanding"),
        }
        cache.write("yfinance", f"info:{ticker}", data)
        return data
