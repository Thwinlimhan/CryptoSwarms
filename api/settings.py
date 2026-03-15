"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CryptoSwarms API"
    environment: str = "local"
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: str = Field(default="dev-key-123", alias="API_KEY")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:80,http://127.0.0.1:80",
        alias="CORS_ORIGINS",
    )
    ssl_certfile: str = Field(default="", alias="SSL_CERTFILE")
    ssl_keyfile: str = Field(default="", alias="SSL_KEYFILE")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    timescaledb_host: str = Field(default="localhost", alias="TIMESCALEDB_HOST")
    timescaledb_port: int = Field(default=5432, alias="TIMESCALEDB_PORT")
    timescaledb_user: str = Field(default="postgres", alias="TIMESCALEDB_USER")
    timescaledb_password: str = Field(default="postgres", alias="TIMESCALEDB_PASSWORD")
    timescaledb_db: str = Field(default="cryptoswarms", alias="TIMESCALEDB_DB")

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="neo4j", alias="NEO4J_PASSWORD")

    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")

    sglang_host: str = Field(default="localhost", alias="SGLANG_HOST")
    sglang_port: int = Field(default=30000, alias="SGLANG_PORT")
    hyperspace_node_url: str = Field(default="http://localhost:8080/v1", alias="HYPERSPACE_NODE_URL")

    exchange_name: str = Field(default="binance", alias="EXCHANGE_NAME")
    exchange_api_key: str = Field(default="", alias="EXCHANGE_API_KEY")
    exchange_api_secret: str = Field(default="", alias="EXCHANGE_API_SECRET")
    exchange_passphrase: str = Field(default="", alias="EXCHANGE_PASSPHRASE")

    # Scanner calibration
    scanner_breakout_confidence: float = Field(default=0.78, alias="SCANNER_BREAKOUT_CONFIDENCE")
    scanner_funding_confidence: float = Field(default=0.72, alias="SCANNER_FUNDING_CONFIDENCE")
    scanner_smart_money_confidence: float = Field(default=0.70, alias="SCANNER_SMART_MONEY_CONFIDENCE")
    scanner_cooldown_cycles: int = Field(default=5, alias="SCANNER_COOLDOWN_CYCLES")

    hyperliquid_api_url: str = Field(default="http://localhost:3001", alias="HYPERLIQUID_API_URL")
    hyperliquid_ws_url: str = Field(default="ws://localhost:3001/ws", alias="HYPERLIQUID_WS_URL")
    hyperliquid_wallet: str = Field(default="0x000000000000000000000000000000000000paper", alias="HYPERLIQUID_WALLET")
    hyperliquid_mode: str = Field(default="paper", alias="HYPERLIQUID_MODE")


settings = Settings()
