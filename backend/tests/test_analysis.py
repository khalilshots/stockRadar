from agents.team2 import breakout_agent, momentum_agent, reversal_agent, risk_agent, scoring_agent
from agents.team2.setup import SetupVerdict
from tests.helpers import breakout_frame, reversal_frame, uptrend_frame
from utils import llm
from utils.indicators import snapshot


def test_breakout_found_on_breakout_day():
    res = breakout_agent.run(snapshot("BRK", breakout_frame()))
    assert res["passed"] and res["data"]["checks"]["above 20d high"]


def test_no_breakout_inside_the_range():
    frame = breakout_frame().iloc[:-1]
    res = breakout_agent.run(snapshot("BRK", frame))
    assert not res["passed"] and "above 20d high" in res["reason"]


def test_reversal_found_after_a_slide():
    assert reversal_agent.run(snapshot("REV", reversal_frame()))["passed"]


def test_reversal_not_found_in_an_uptrend():
    assert not reversal_agent.run(snapshot("UP", uptrend_frame()))["passed"]


def test_momentum_in_an_uptrend():
    res = momentum_agent.run(snapshot("UP", uptrend_frame()))
    assert res["passed"], res["reason"]


def test_llm_cannot_invent_a_setup_the_numbers_dont_show(monkeypatch):
    called = []
    monkeypatch.setattr(llm, "ask", lambda *a, **k: called.append(1) or SetupVerdict(present=True, score=99, reason="trust me"))
    res = breakout_agent.run(snapshot("BRK", breakout_frame().iloc[:-1]))
    assert not res["passed"]
    assert called == []


def test_llm_grades_a_real_setup(monkeypatch):
    monkeypatch.setattr(llm, "ask", lambda *a, **k: SetupVerdict(present=True, score=82, reason="clean break on 6x volume"))
    res = breakout_agent.run(snapshot("BRK", breakout_frame()))
    assert res["passed"] and res["source"] == "llm" and res["data"]["score"] == 82


def test_risk_sizes_to_the_dollar_risk():
    snap = {"ticker": "ABCD", "price": 10.0, "atr_14": 0.4, "avg_volume_20": 1_000_000}
    res = risk_agent.run(snap, risk_per_trade=500)
    plan = res["data"]
    assert plan["stop"] == 9.4
    assert plan["shares"] == 833            # 500 / 0.60
    assert plan["max_loss"] <= 500
    assert plan["target_1"] == 11.2         # 2R
    assert plan["target_2"] == 11.8         # 3R


def test_risk_halves_size_when_vix_is_elevated():
    snap = {"ticker": "ABCD", "price": 10.0, "atr_14": 0.4}
    calm = risk_agent.run(snap, 500, {"regime": "normal", "vix": 15})["data"]["shares"]
    scared = risk_agent.run(snap, 500, {"regime": "elevated", "vix": 27})["data"]["shares"]
    assert scared == calm // 2


def test_risk_rejects_a_stop_that_is_too_wide():
    res = risk_agent.run({"ticker": "WILD", "price": 3.0, "atr_14": 0.6}, 500)
    assert not res["passed"] and "too volatile" in res["reason"]


def test_score_treats_missing_inputs_as_neutral():
    setup = {"data": {"score": 80}}
    catalyst = {"data": {"strength": None}}
    total, parts = scoring_agent.score(setup, catalyst, {"relative_volume": 5.0}, None)
    assert parts == {"setup": 80, "catalyst": 50, "volume": 100, "sentiment": 50}
    assert total == round(80 * 0.5 + 50 * 0.2 + 100 * 0.15 + 50 * 0.15)
