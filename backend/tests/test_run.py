from run import summarize_drops


def test_drop_reasons_are_grouped_by_rule():
    dropped = [
        {"agent": "price_filter", "reason": "gap 0.0% is under the 10% minimum"},
        {"agent": "price_filter", "reason": "gap 2.16% is under the 10% minimum"},
        {"agent": "price_filter", "reason": "price $1.66 is outside $2-$20"},
        {"agent": "volume_agent", "reason": "relative volume 0.8x is under 1.5x"},
        {"agent": "setup_gate", "reason": "no momentum, breakout setup"},
    ]
    assert summarize_drops(dropped) == [
        ("price_filter: gap under the minimum", 2),
        ("price_filter: price outside the strategy's range", 1),
        ("volume_agent: relative volume too low", 1),
        ("setup_gate: no matching setup", 1),
    ]
