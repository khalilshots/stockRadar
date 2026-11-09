from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # api keys, all optional
    finnhub_key: str = ""
    alpha_vantage_key: str = ""
    fred_key: str = ""
    newsapi_key: str = ""

    # free tier limits
    alpha_vantage_daily_limit: int = 25
    alpha_vantage_per_scan: int = 10
    newsapi_daily_limit: int = 100
    finnhub_calls_per_minute: int = 60
    fred_daily_limit: int = 500

    # llm
    llm_model: str = "ollama/llama3.2:3b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 400
    llm_timeout: int = 60

    # pipeline limits
    max_universe_size: int = 500
    max_watchlist_size: int = 50
    max_final_list_size: int = 10
    history_period: str = "6mo"
    news_lookback_days: int = 3

    # scheduler (eastern time)
    scheduler_enabled: bool = False
    default_strategy: str = "Small Cap Momentum"
    premarket_scan: str = "9:00"
    postmarket_scan: str = "16:30"
    night_scan: str = "22:00"

    # paths
    data_dir: Path = DATA_DIR
    scans_dir: Path = DATA_DIR / "scans"
    cache_dir: Path = DATA_DIR / "cache"
    usage_path: Path = DATA_DIR / "usage.json"
    strategies_path: Path = BACKEND_DIR / "strategies" / "strategies.json"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_model) and self.llm_model.lower() != "none"

    def sources(self) -> dict:
        return {
            "yfinance": True,
            "finnhub": bool(self.finnhub_key),
            "alpha_vantage": bool(self.alpha_vantage_key),
            "fred": bool(self.fred_key),
            "newsapi": bool(self.newsapi_key),
        }


settings = Settings()
