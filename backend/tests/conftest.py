import shutil

import pytest

from config.settings import settings
from utils import llm


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test gets its own data folder, no api keys, and no LLM unless it patches one in."""
    strategies = tmp_path / "strategies.json"
    shutil.copy(settings.strategies_path, strategies)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "scans_dir", tmp_path / "scans")
    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "usage_path", tmp_path / "usage.json")
    monkeypatch.setattr(settings, "strategies_path", strategies)
    monkeypatch.setattr(settings, "llm_model", "none")
    for key in ("finnhub_key", "alpha_vantage_key", "fred_key", "newsapi_key"):
        monkeypatch.setattr(settings, key, "")
    llm.reset()
    yield
    llm.reset()
