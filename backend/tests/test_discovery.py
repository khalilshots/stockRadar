import pytest

from agents.team1 import catalyst_agent, price_filter, volume_agent
from strategies.strategy_manager import Criteria
from tools.http import SourceUnavailable
from utils import llm
from utils.gates import check_gate

CRITERIA = Criteria(price_min=2, price_max=20, max_float=10_000_000, min_volume=50_000,
                    min_relative_volume=1.5, min_gap_percent=10, max_prior_day_gain=40, require_catalyst=True)


def snap(**overrides):
    base = {"ticker": "ABCD", "price": 6.4, "gap_percent": 12.0, "prior_day_gain": 3.0, "volume": 1_350_000,
            "relative_volume": 4.2, "change_percent": 15.0}
    return {**base, **overrides}


def fundamentals(float_shares=8_200_000):
    return lambda ticker: {"float_shares": float_shares, "name": "ABCD Corp"}


def test_price_filter_passes_a_small_cap_gapper():
    res = price_filter.run(snap(), CRITERIA, fundamentals())
    assert check_gate(res)
    assert res["data"]["float_shares"] == 8_200_000


@pytest.mark.parametrize("overrides, words", [
    ({"price": 150.0}, "outside"),
    ({"gap_percent": 4.0}, "gap"),
    ({"prior_day_gain": 55.0}, "already ran"),
])
def test_price_filter_failures(overrides, words):
    res = price_filter.run(snap(**overrides), CRITERIA, fundamentals())
    assert not check_gate(res)
    assert words in res["reason"]


def test_float_lookup_only_happens_after_price_passes():
    calls = []

    def lookup(ticker):
        calls.append(ticker)
        return {"float_shares": 1}

    price_filter.run(snap(price=150.0), CRITERIA, lookup)
    assert calls == []
    price_filter.run(snap(), CRITERIA, lookup)
    assert calls == ["ABCD"]


def test_missing_float_is_dropped_as_missing_data():
    res = price_filter.run(snap(), CRITERIA, fundamentals(None))
    assert res["data_missing"] and not check_gate(res)


def test_float_too_big():
    res = price_filter.run(snap(), CRITERIA, fundamentals(50_000_000))
    assert not check_gate(res) and "float" in res["reason"]


def test_volume_agent():
    assert check_gate(volume_agent.run(snap(), CRITERIA))
    assert not check_gate(volume_agent.run(snap(volume=10_000), CRITERIA))
    assert not check_gate(volume_agent.run(snap(relative_volume=1.1), CRITERIA))


def news(*headlines):
    return lambda ticker, company=None: [{"headline": h, "summary": "", "source": "t", "url": "u", "published": 1} for h in headlines]


def test_catalyst_skipped_without_news_keys():
    res = catalyst_agent.run(snap(), CRITERIA, None)
    assert check_gate(res) and res["source"] == "skipped"


def test_catalyst_api_outage_drops_when_required():
    def down(ticker, company=None):
        raise SourceUnavailable("finnhub: request failed")
    res = catalyst_agent.run(snap(), CRITERIA, down)
    assert res["data_missing"]


def test_no_news_fails_when_catalyst_required():
    assert not check_gate(catalyst_agent.run(snap(), CRITERIA, news()))


def test_rules_pick_up_positive_and_negative_news():
    good = catalyst_agent.run(snap(), CRITERIA, news("ABCD wins $40M Army contract"))
    assert check_gate(good) and good["data"]["catalyst_type"] == "contract"

    bad = catalyst_agent.run(snap(), CRITERIA, news("ABCD announces $10M registered direct offering"))
    assert not check_gate(bad) and "negative" in bad["reason"]


def test_llm_verdict_is_used_when_available(monkeypatch):
    verdict = catalyst_agent.CatalystVerdict(has_catalyst=True, catalyst_type="fda", sentiment="positive",
                                             strength=85, headline="ABCD gets FDA nod", reason="FDA approval")
    monkeypatch.setattr(llm, "ask", lambda *a, **k: verdict)
    res = catalyst_agent.run(snap(), CRITERIA, news("ABCD gets FDA nod"))
    assert check_gate(res)
    assert res["source"] == "llm" and res["data"]["strength"] == 85
