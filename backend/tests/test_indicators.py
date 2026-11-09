import pandas as pd

from tests.helpers import bars, breakout_frame, reversal_frame
from utils.indicators import atr, down_streak, rsi, snapshot


def test_rsi_is_100_when_price_only_rises():
    assert rsi(pd.Series(range(1, 30), dtype=float)).iloc[-1] == 100


def test_rsi_is_low_when_price_only_falls():
    assert rsi(pd.Series(range(30, 1, -1), dtype=float)).iloc[-1] < 5


def test_atr_matches_a_constant_range():
    df = bars([10.0] * 30, spread=0.5)
    assert round(atr(df).iloc[-1], 4) == 1.0


def test_down_streak_counts_back_from_yesterday():
    # three red days, then today (ignored)
    assert down_streak(pd.Series([10, 11, 10.5, 10, 9.5, 12], dtype=float)) == 3


def test_snapshot_on_breakout_day():
    snap = snapshot("BRK", breakout_frame())
    assert snap["price"] == 5.95
    assert snap["prev_close"] == 4.6
    assert snap["gap_percent"] == round((5.5 - 4.6) / 4.6 * 100, 2)
    assert snap["relative_volume"] == 6.0
    # 20 day high is measured before today, so today can break it
    assert snap["high_20"] == 5.1
    assert snap["price"] > snap["high_20"]


def test_snapshot_reversal_numbers():
    snap = snapshot("REV", reversal_frame())
    assert snap["down_streak"] >= 3
    assert snap["pct_from_high_20"] < -15
    assert snap["change_percent"] > 0
