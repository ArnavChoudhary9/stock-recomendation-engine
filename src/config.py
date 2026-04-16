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


def clear_cache() -> None:
    """Clear cached configs — primarily useful in tests."""
    load_data_config.cache_clear()
