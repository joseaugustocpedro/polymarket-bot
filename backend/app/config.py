from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Polymarket Alert Bot"
    database_url: str = "sqlite:///./polymarket_bot.db"
    poll_interval_seconds: int = 30

    # Carteiras carregadas automaticamente no primeiro startup.
    # Formato: "Alias:0xEndereco,Outro Alias:0xEndereco"
    default_wallets: str = "FullPicks1:0x9b1e0334569aa1768a07705a859686aad58e82c9"
    alert_on_backfill: bool = False

    polymarket_data_api: str = "https://data-api.polymarket.com"
    polymarket_gamma_api: str = "https://gamma-api.polymarket.com"
    polymarket_clob_api: str = "https://clob.polymarket.com"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None

    paper_trading: bool = True
    enable_live_trading: bool = False
    max_trade_usd: float = 25.0
    daily_loss_limit_usd: float = 50.0
    allowed_market_keywords: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
