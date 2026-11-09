import json

from pydantic import BaseModel, Field

from config.settings import settings


class Criteria(BaseModel):
    price_min: float = 0
    price_max: float = 1_000_000
    max_float: float | None = None
    min_volume: int = 0
    min_relative_volume: float = 0
    min_gap_percent: float = -100
    max_prior_day_gain: float = 1_000
    require_catalyst: bool = False


class Strategy(BaseModel):
    id: str
    name: str
    criteria: Criteria
    setup_preferences: list[str] = Field(default_factory=list)
    risk_per_trade: float = 100
    universe: list[str] = Field(default_factory=lambda: ["most_actives"])


def load_all() -> list[Strategy]:
    path = settings.strategies_path
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [Strategy(**s) for s in data.get("strategies", [])]


def get_strategy(name: str) -> Strategy | None:
    for strategy in load_all():
        if strategy.name.lower() == name.lower():
            return strategy
    return None


def save_strategy(strategy: Strategy) -> Strategy:
    """Add a strategy, or overwrite the one with the same name."""
    strategies = load_all()
    for i, existing in enumerate(strategies):
        if existing.name.lower() == strategy.name.lower():
            strategies[i] = strategy
            break
    else:
        strategies.append(strategy)
    _write(strategies)
    return strategy


def delete_strategy(name: str) -> bool:
    strategies = load_all()
    kept = [s for s in strategies if s.name.lower() != name.lower()]
    if len(kept) == len(strategies):
        return False
    _write(kept)
    return True


def _write(strategies: list[Strategy]) -> None:
    payload = {"strategies": [s.model_dump() for s in strategies]}
    settings.strategies_path.write_text(json.dumps(payload, indent=2) + "\n")
