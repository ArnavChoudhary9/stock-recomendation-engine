"""Unit tests for the SQLite watchlist methods."""

from __future__ import annotations

import pytest

from src.data.repositories.sqlite import SQLiteStockRepository


@pytest.mark.asyncio
async def test_add_and_list_watchlist(sqlite_repo: SQLiteStockRepository) -> None:
    await sqlite_repo.add_to_watchlist("tcs", notes="IT bellwether")
    await sqlite_repo.add_to_watchlist("RELIANCE")
    items = await sqlite_repo.list_watchlist()
    assert [i.symbol for i in items] == ["TCS", "RELIANCE"]
    assert items[0].notes == "IT bellwether"
    assert items[1].notes is None


@pytest.mark.asyncio
async def test_add_is_idempotent_preserves_added_at(
    sqlite_repo: SQLiteStockRepository,
) -> None:
    first = await sqlite_repo.add_to_watchlist("TCS")
    second = await sqlite_repo.add_to_watchlist("TCS", notes="new note")
    assert second.added_at == first.added_at
    assert second.notes == "new note"


@pytest.mark.asyncio
async def test_get_watchlist_item(sqlite_repo: SQLiteStockRepository) -> None:
    await sqlite_repo.add_to_watchlist("INFY", notes="peer")
    item = await sqlite_repo.get_watchlist_item("infy")
    assert item is not None
    assert item.symbol == "INFY"
    assert item.notes == "peer"
    assert await sqlite_repo.get_watchlist_item("UNKNOWN") is None


@pytest.mark.asyncio
async def test_remove_from_watchlist(sqlite_repo: SQLiteStockRepository) -> None:
    await sqlite_repo.add_to_watchlist("TCS")
    assert await sqlite_repo.remove_from_watchlist("TCS") is True
    assert await sqlite_repo.list_watchlist() == []
    # Removing a non-existent entry returns False, doesn't raise.
    assert await sqlite_repo.remove_from_watchlist("TCS") is False


@pytest.mark.asyncio
async def test_watchlist_does_not_require_stock_row(
    sqlite_repo: SQLiteStockRepository,
) -> None:
    """Adding to the watchlist must not require a pre-existing stock record."""
    item = await sqlite_repo.add_to_watchlist("NEWLISTING")
    assert item.symbol == "NEWLISTING"
