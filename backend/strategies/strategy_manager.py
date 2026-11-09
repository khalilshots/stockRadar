import json
from pathlib import Path

STRATEGIES_FILE = Path(__file__).parent / "strategies.json"


def load_all() -> list:
    """Return all strategies, or [] if the file doesn't exist."""
    if not STRATEGIES_FILE.exists():
        return []

    with open(STRATEGIES_FILE, "r") as f:
        data = json.load(f)

    return data.get("strategies", [])


def get_strategy(name: str) -> dict | None:
    """Return the strategy with this name, or None."""
    strategies = load_all()

    for strategy in strategies:
        if strategy["name"] == name:
            return strategy

    print(f"Strategy '{name}' not found")
    return None


def save_strategy(strategy: dict) -> None:
    """Add a strategy, overwriting any existing one with the same name."""
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