from agents.orchestrator import Sources, run_scan
from strategies.strategy_manager import get_strategy
from tests.helpers import FakeMarket, bars, breakout_frame, news_for


def market():
    frames = {
        "BRK": breakout_frame(),                                  # should make the final list
        "BIG": bars([150.0] * 59 + [170.0]),                     # price too high
        "THIN": bars([4.0] * 59 + [4.6], volumes=[1_000] * 60, opens=[4.0] * 59 + [4.6]),  # gaps but no volume
        "NOFLT": breakout_frame(),                                # float unknown
        "DIL": breakout_frame(),                                  # offering headline
    }
    fundamentals = {
        "BRK": {"name": "Breakout Co", "float_shares": 5_000_000},
        "THIN": {"float_shares": 3_000_000},
        "DIL": {"float_shares": 4_000_000},
    }
    return FakeMarket(frames, fundamentals, screen=list(frames) + ["GONE"])


def sources(m=None, **extra):
    news = news_for({
        "BRK": ["Breakout Co wins $40M Navy contract"],
        "DIL": ["DIL prices $8M public offering of common stock"],
    })
    return Sources(market=m or market(), news=news, **extra)


def test_full_scan_keeps_only_the_real_setup():
    updates = []
    scan = run_scan(get_strategy("Small Cap Momentum"), sources=sources(), on_update=updates.append)

    assert scan["status"] == "done", scan["error"]
    assert [c["ticker"] for c in scan["final"]] == ["BRK"]

    final = scan["final"][0]
    assert final["setup"] in ("breakout", "momentum")
    assert final["catalyst"]["type"] == "contract"
    assert final["plan"]["shares"] > 0 and final["plan"]["stop"] < final["price"]

    why = {d["ticker"]: (d["agent"], d["reason"]) for d in scan["dropped"]}
    assert why["GONE"][0] == "market_data"
    assert why["BIG"][0] == "price_filter"
    assert why["THIN"][0] == "volume_agent"
    assert why["NOFLT"][0] == "price_filter" and "float" in why["NOFLT"][1]
    assert why["DIL"][0] == "catalyst_agent"

    assert scan["counts"] == {"universe": 6, "with_data": 5, "watchlist": 1, "analysis_passed": 1, "final": 1}
    assert updates and updates[-1]["status"] == "done"


def test_every_agent_shows_up_in_the_trace():
    scan = run_scan(get_strategy("Small Cap Momentum"), sources=sources())
    agents = [step["agent"] for step in scan["traces"]["BRK"]]
    assert agents == ["price_filter", "volume_agent", "catalyst_agent", "momentum_agent",
                      "breakout_agent", "reversal_agent", "risk_agent", "scoring_agent"]


def test_manual_tickers_skip_the_screens():
    scan = run_scan(get_strategy("Small Cap Momentum"), tickers=["brk", " BIG", "BRK"], sources=sources())
    assert scan["counts"]["universe"] == 2


def test_vix_regime_halves_position_size():
    calm = run_scan(get_strategy("Small Cap Momentum"), sources=sources(regime=lambda: {"vix": 14, "regime": "normal"}))
    scared = run_scan(get_strategy("Small Cap Momentum"), sources=sources(regime=lambda: {"vix": 31, "regime": "high_volatility"}))
    assert scared["final"][0]["plan"]["shares"] < calm["final"][0]["plan"]["shares"]


def test_sentiment_feeds_the_score():
    neutral = run_scan(get_strategy("Small Cap Momentum"), sources=sources())
    bullish = run_scan(get_strategy("Small Cap Momentum"), sources=sources(sentiment=lambda t: {"score": 0.6, "label": "Bullish", "articles": 4}))
    assert bullish["final"][0]["score"] > neutral["final"][0]["score"]


def test_scan_with_the_llm_on(monkeypatch):
    import litellm
    from types import SimpleNamespace

    from config.settings import settings

    def fake_completion(**kw):
        system = kw["messages"][0]["content"]
        if "news headlines" in system:
            text = '{"has_catalyst": true, "catalyst_type": "contract", "sentiment": "positive", "strength": 80, "headline": "Breakout Co wins $40M Navy contract", "reason": "new Navy contract"}'
        elif "trade notes" in system:
            text = '{"summary": "Broke out of a two month range on a Navy contract. Fails if it loses $4.97."}'
        else:
            text = '{"present": true, "score": 77, "reason": "clean setup"}'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    monkeypatch.setattr(settings, "llm_model", "ollama/llama3.2:3b")
    monkeypatch.setattr(litellm, "completion", fake_completion)
    scan = run_scan(get_strategy("Small Cap Momentum"), sources=sources())

    final = scan["final"][0]
    assert scan["llm"]["used"]
    assert final["catalyst"]["source"] == "llm"
    assert final["setup_score"] == 77
    assert final["summary"].startswith("Broke out")


def test_a_crash_marks_the_scan_failed():
    class Broken(FakeMarket):
        def history(self, tickers, period=None):
            raise RuntimeError("yahoo is down")

    scan = run_scan(get_strategy("Small Cap Momentum"), sources=sources(Broken({}, {}, screen=["X"])))
    assert scan["status"] == "failed" and "yahoo is down" in scan["error"]
