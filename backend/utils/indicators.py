import math

import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    return (100 - 100 / (1 + rs)).fillna(100)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    true_range = pd.concat(
        [df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def _num(value, digits: int = 2):
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) or math.isinf(value) else round(value, digits)


def _pct(a, b):
    return (a - b) / b * 100 if b else None


def down_streak(close: pd.Series) -> int:
    """How many days in a row the close fell, counting back from yesterday."""
    streak = 0
    closes = close.iloc[:-1].tolist()
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            streak += 1
        else:
            break
    return streak


def snapshot(ticker: str, df: pd.DataFrame) -> dict:
    """
    Everything the agents need about one ticker, computed from daily bars.
    The last row is treated as today. Lookback windows exclude today so a
    breakout is measured against levels that existed before it.
    """
    close = df["Close"]
    today, yesterday = df.iloc[-1], df.iloc[-2]
    n = len(df)

    prior = df.iloc[-21:-1]
    avg_volume = prior["Volume"].mean()
    high_20 = prior["High"].max()
    low_20 = prior["Low"].min()

    sma20 = close.rolling(20).mean().iloc[-1] if n >= 20 else None
    sma50 = close.rolling(50).mean().iloc[-1] if n >= 50 else None
    price = today["Close"]

    return {
        "ticker": ticker,
        "price": _num(price, 4),
        "open": _num(today["Open"], 4),
        "high": _num(today["High"], 4),
        "low": _num(today["Low"], 4),
        "prev_close": _num(yesterday["Close"], 4),
        "volume": int(today["Volume"]) if not math.isnan(today["Volume"]) else 0,
        "avg_volume_20": _num(avg_volume, 0),
        "relative_volume": _num(today["Volume"] / avg_volume if avg_volume else None),
        "gap_percent": _num(_pct(today["Open"], yesterday["Close"])),
        "change_percent": _num(_pct(price, yesterday["Close"])),
        "prior_day_gain": _num(_pct(yesterday["Close"], df.iloc[-3]["Close"])) if n >= 3 else None,
        "change_5d": _num(_pct(price, close.iloc[-6])) if n >= 6 else None,
        "rsi_14": _num(rsi(close).iloc[-1], 1) if n >= 15 else None,
        "atr_14": _num(atr(df).iloc[-1], 4) if n >= 15 else None,
        "sma_20": _num(sma20, 4),
        "sma_50": _num(sma50, 4),
        "high_20": _num(high_20, 4),
        "low_20": _num(low_20, 4),
        "pct_from_high_20": _num(_pct(price, high_20)),
        "down_streak": down_streak(close),
        "bars": n,
    }
