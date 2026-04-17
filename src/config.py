"""YAML config loader with environment variable interpolation.

Each module has its own YAML file in ``config/``. Secrets are referenced as
``${VAR_NAME}`` and resolved from process env at load time. Loads are cached
by path so dependency-injected services share one config instance.
"""

from __future__ import annotations

import os
import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.contracts import (
    IndicatorPeriods,
    ScoringConfig,
    ScoringWeights,
    SignalThresholds,
)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigError(Exception):
    """Raised when a config file is missing, malformed, or references an unset env var."""


class StorageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path = Field(default=Path("data/stocks.db"))
    wal_mode: bool = True


class DataProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str = "yahoo"
    default_exchange: str = "NSE"
    staleness_threshold_hours: int = Field(default=24, gt=0)
    backfill_days: int = Field(default=365, gt=0)
    batch_size: int = Field(default=50, gt=0)
    rate_limit_delay_ms: int = Field(default=500, ge=0)


class DataConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: DataProviderConfig = Field(default_factory=DataProviderConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


class NewsProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str = "google_rss"
    time_window_hours: int = Field(default=72, gt=0)
    max_articles_per_stock: int = Field(default=20, gt=0)
    dedup_similarity_threshold: float = Field(default=0.85, ge=0, le=1)
    cache_ttl_minutes: int = Field(default=60, ge=0)
    language: str = "en"
    country: str = "IN"
    request_timeout_seconds: float = Field(default=15.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    backoff_base_seconds: float = Field(default=1.0, ge=0)


class SentimentAnalyzerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    analyzer: str = "textblob"
    min_text_length: int = Field(default=50, ge=0)
    positive_threshold: float = Field(default=0.1, ge=0, le=1)
    negative_threshold: float = Field(default=-0.1, ge=-1, le=0)


class NewsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    news: NewsProviderConfig = Field(default_factory=NewsProviderConfig)
    sentiment: SentimentAnalyzerConfig = Field(default_factory=SentimentAnalyzerConfig)


class LLMProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "anthropic/claude-sonnet-4"
    max_tokens: int = Field(default=1024, gt=0)
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_retries: int = Field(default=3, ge=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    backoff_base_seconds: float = Field(default=1.0, ge=0)
    fallback_models: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm: LLMProviderConfig = Field(default_factory=LLMProviderConfig)


class APIServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8000, gt=0, lt=65536)
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    request_id_header: str = "X-Request-ID"


class APIConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api: APIServerConfig = Field(default_factory=APIServerConfig)


def _interpolate_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match[str]) -> str:
            var = m.group(1)
            env = os.environ.get(var)
            if env is None:
                raise ConfigError(f"Environment variable '{var}' is not set")
            return env

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interpolate_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(v) for v in value]
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and interpolate ``${ENV_VAR}`` placeholders."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    interpolated: dict[str, Any] = _interpolate_env(raw)
    return interpolated


def config_path(name: str, *, config_dir: Path | None = None) -> Path:
    """Resolve ``config/<name>.yaml``, falling back to ``<name>.example.yaml``."""
    base = config_dir or CONFIG_DIR
    primary = base / f"{name}.yaml"
    if primary.exists():
        return primary
    example = base / f"{name}.example.yaml"
    if example.exists():
        return example
    raise ConfigError(f"No config file for '{name}' in {base}")


@cache
def load_data_config(config_dir: Path | None = None) -> DataConfig:
    """Load and validate ``config/data.yaml``."""
    path = config_path("data", config_dir=config_dir)
    return DataConfig.model_validate(load_yaml(path))


@cache
def load_processing_config(config_dir: Path | None = None) -> ScoringConfig:
    """Load ``config/processing.yaml`` into a :class:`ScoringConfig`.

    YAML structure groups keys as ``features:``, ``scoring:``, and ``signals:``,
    so we map them onto the nested model (``periods``, ``weights``, ``signals``).
    """
    path = config_path("processing", config_dir=config_dir)
    raw = load_yaml(path)
    return ScoringConfig(
        periods=IndicatorPeriods.model_validate(raw.get("features", {})),
        weights=ScoringWeights.model_validate(raw.get("scoring", {}).get("weights", {})),
        signals=SignalThresholds.model_validate(raw.get("signals", {})),
    )


@cache
def load_news_config(config_dir: Path | None = None) -> NewsConfig:
    """Load ``config/news.yaml`` into a :class:`NewsConfig`."""
    path = config_path("news", config_dir=config_dir)
    return NewsConfig.model_validate(load_yaml(path))


@cache
def load_llm_config(config_dir: Path | None = None) -> LLMConfig:
    """Load ``config/llm.yaml`` into a :class:`LLMConfig`."""
    path = config_path("llm", config_dir=config_dir)
    return LLMConfig.model_validate(load_yaml(path))


@cache
def load_api_config(config_dir: Path | None = None) -> APIConfig:
    """Load ``config/api.yaml`` into an :class:`APIConfig`.

    YAML uses ``api.cors.allowed_origins``; the model flattens it to
    ``cors_allowed_origins`` for convenience.
    """
    path = config_path("api", config_dir=config_dir)
    raw = load_yaml(path)
    api_block = raw.get("api", {})
    cors_block = api_block.get("cors") or {}
    flat = {
        "host": api_block.get("host", "127.0.0.1"),
        "port": api_block.get("port", 8000),
        "cors_allowed_origins": cors_block.get("allowed_origins", ["*"]),
        "request_id_header": api_block.get("request_id_header", "X-Request-ID"),
    }
    return APIConfig(api=APIServerConfig.model_validate(flat))


def clear_cache() -> None:
    """Clear cached configs — primarily useful in tests."""
    load_data_config.cache_clear()
    load_processing_config.cache_clear()
    load_news_config.cache_clear()
    load_llm_config.cache_clear()
    load_api_config.cache_clear()
