"""Unit tests for the YAML config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import (
    ConfigError,
    DataConfig,
    clear_cache,
    load_data_config,
    load_yaml,
)


def test_load_yaml_interpolates_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_KEY", "secret-123")
    path = tmp_path / "c.yaml"
    path.write_text("api:\n  key: ${MY_KEY}\n")
    data = load_yaml(path)
    assert data == {"api": {"key": "secret-123"}}


def test_load_yaml_missing_env_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
    path = tmp_path / "c.yaml"
    path.write_text("x: ${DOES_NOT_EXIST}\n")
    with pytest.raises(ConfigError):
        load_yaml(path)


def test_load_yaml_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_yaml(tmp_path / "nope.yaml")


def test_load_data_config_with_example(tmp_path: Path) -> None:
    clear_cache()
    # Only example file present — loader falls back to it.
    (tmp_path / "data.example.yaml").write_text(
        "data:\n  provider: yahoo\n  backfill_days: 90\n"
        "storage:\n  path: data/test.db\n  wal_mode: false\n"
    )
    cfg = load_data_config(config_dir=tmp_path)
    assert isinstance(cfg, DataConfig)
    assert cfg.data.provider == "yahoo"
    assert cfg.data.backfill_days == 90
    assert cfg.storage.wal_mode is False
    clear_cache()


def test_load_data_config_prefers_primary(tmp_path: Path) -> None:
    clear_cache()
    (tmp_path / "data.example.yaml").write_text("data:\n  provider: example\n")
    (tmp_path / "data.yaml").write_text("data:\n  provider: primary\n")
    cfg = load_data_config(config_dir=tmp_path)
    assert cfg.data.provider == "primary"
    clear_cache()
