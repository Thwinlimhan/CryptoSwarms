"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CryptoSwarms API"
    environment: str = "local"
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
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

    exchange_name: str = Field(default="binance", alias="EXCHANGE_NAME")
    exchange_api_key: str = Field(default="", alias="EXCHANGE_API_KEY")
    exchange_api_secret: str = Field(default="", alias="EXCHANGE_API_SECRET")
    exchange_passphrase: str = Field(default="", alias="EXCHANGE_PASSPHRASE")


settings = Settings()
