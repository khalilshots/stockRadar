import pandas as pd


def bars(closes, volumes=None, opens=None, highs=None, lows=None, spread=0.15) -> pd.DataFrame:
    """Daily bars from a list of closes. Opens default to the prior close."""
    n = len(closes)
    volumes = volumes or [200_000] * n
    opens = opens or [closes[0]] + list(closes[:-1])
    highs = highs or [max(o, c) + spread for o, c in zip(opens, closes)]
    lows = lows or [min(o, c) - spread for o, c in zip(opens, closes)]
    index = pd.bdate_range(end="2026-11-06", periods=n)
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes}, index=index)


def breakout_frame() -> pd.DataFrame:
    """Small cap chopping between 4.6 and 5.0 for 59 days, then gapping up through the range on 6x volume."""
    closes = [4.8 + (0.2 if i % 2 else -0.2) for i in range(59)] + [5.95]
    opens = [closes[0]] + closes[:-2] + [5.5]
    volumes = [200_000] * 59 + [1_200_000]
    highs = [max(o, c) + 0.1 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.1 for o, c in zip(opens, closes)]
    highs[-1], lows[-1] = 6.0, 5.45
    return bars(closes, volumes, opens, highs, lows)


def reversal_frame() -> pd.DataFrame:
    """Steady 30 day slide from 50 to about 35, then a green day."""
    closes = [50.0] * 30 + [50 - i * 0.5 for i in range(1, 31)] + [36.2]
    volumes = [800_000] * 60 + [1_000_000]
    return bars(closes, volumes, spread=0.6)


def uptrend_frame() -> pd.DataFrame:
    """Grinding higher for 60 days with a pullback every third day, so RSI stays under 85."""
    closes, price = [], 10.0
    for i in range(60):
        price += -0.1 if i % 3 == 2 else 0.2
        closes.append(round(price, 2))
    volumes = [500_000] * 59 + [900_000]
    return bars(closes, volumes, spread=0.1)


class FakeMarket:
    def __init__(self, frames: dict, fundamentals: dict, screen: list[str] | None = None):
        self.frames = frames
        self._fundamentals = fundamentals
        self.screen = screen or list(frames)
        self.fundamental_calls = []

    def universe(self, screens, limit):
        return self.screen[:limit]

    def history(self, tickers, period=None):
        return {t: self.frames[t] for t in tickers if t in self.frames}

    def fundamentals(self, ticker):
        self.fundamental_calls.append(ticker)
        return self._fundamentals.get(ticker, {})


def news_for(headlines: dict[str, list[str]]):
    def get_news(ticker, company=None):
        return [{"headline": h, "summary": "", "source": "test", "url": f"https://example.com/{ticker}/{i}", "published": 1_700_000_000 - i}
                for i, h in enumerate(headlines.get(ticker, []))]
    return get_news
