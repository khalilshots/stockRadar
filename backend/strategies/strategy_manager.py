# strategies/strategy_manager.py

import json
from pathlib import Path

STRATEGIES_FILE = Path(__file__).parent / "strategies.json"


def load_all() -> list:
    """
    Read strategies.json and return the list of strategies.
    Returns empty list if file doesn't exist yet.
    """
    if not STRATEGIES_FILE.exists():
        return []

    with open(STRATEGIES_FILE, "r") as f:
        data = json.load(f)

    return data.get("strategies", [])


def get_strategy(name: str) -> dict | None:
    """
    Find a strategy by name.
    Returns None if not found.
    """
    strategies = load_all()

    for strategy in strategies:
        if strategy["name"] == name:
            return strategy

    print(f"Strategy '{name}' not found")
    return None


def save_strategy(strategy: dict) -> None:
    """
    Add a new strategy to strategies.json.
    If a strategy with the same name exists, overwrite it.
    """
    strategies = load_all()

    for i, existing in enumerate(strategies):
        if existing["name"] == strategy["name"]:
            strategies[i] = strategy
            print(f"Updated existing strategy: {strategy['name']}")
            _write(strategies)
            return

    strategies.append(strategy)
    print(f"Saved new strategy: {strategy['name']}")
    _write(strategies)


def _write(strategies: list) -> None:
    with open(STRATEGIES_FILE, "w") as f:
        json.dump({"strategies": strategies}, f, indent=2)