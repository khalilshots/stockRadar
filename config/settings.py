from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    """App settings, loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # api keys
    alpha_vantage_key: str = Field(..., description="Alpha Vantage API key")
    finnhub_key: str = Field(..., description="Finnhub API key")
    fred_key: str = Field(..., description="FRED API key")
    newsapi_key: str = Field(..., description="NewsAPI key")

    reddit_client_id: str = Field(..., description="Reddit app client ID")
    reddit_client_secret: str = Field(..., description="Reddit app client secret")
    reddit_user_agent: str = Field(default="stock-radar/1.0")

    # free tier limits
    alpha_vantage_daily_limit: int = 25
    newsapi_daily_limit: int = 100
    finnhub_calls_per_minute: int = 60

    yfinance_session_limit: int = 500
    fred_session_limit: int = 500

    # paths
    universe_path: Path = ROOT_DIR / "data" / "universe.json"
    watchlist_path: Path = ROOT_DIR / "data" / "watchlist.json"
    final_list_path: Path = ROOT_DIR / "data" / "final_list.json"
    outcomes_path: Path = ROOT_DIR / "data" / "outcomes.json"
    strategies_path: Path = ROOT_DIR / "strategies" / "strategies.json"

    # llm
    llm_model: str = "ollama/llama3.2"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 512

    # session windows (EST, 24h)
    night_session_start: int = 22   # 10 PM
    night_session_end: int = 24     # midnight
    premarket_session_start: int = 9
    premarket_session_end_hour: int = 9
    premarket_session_end_minute: int = 20
    postmarket_session_start: int = 16  # 4 PM
    postmarket_session_end: int = 18    # 6 PM

    # pipeline limits
    max_universe_size: int = 500
    max_watchlist_size: int = 50
    max_final_list_size: int = 10


settings = Settings()