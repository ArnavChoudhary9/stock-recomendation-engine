"""Scheduled background jobs.

Daily post-market-close job refreshes OHLCV + fundamentals for all tracked
symbols. Schedule time is IST (Asia/Kolkata) because that is when the market
closes; APScheduler handles the timezone conversion.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.data.service import DataService

log = logging.getLogger(__name__)

IST = "Asia/Kolkata"


async def refresh_all_symbols(service: DataService) -> dict[str, int]:
    """Refresh every tracked symbol. Invoked by the scheduler or on-demand."""
    stocks = await service.repo.list_symbols()
    symbols = [s.symbol for s in stocks]
    if not symbols:
        log.info("refresh_all_symbols: no tracked stocks")
        return {}
    log.info("refresh_all_symbols: refreshing %d symbols", len(symbols))
    return await service.refresh_many(symbols)


def build_scheduler(
    service: DataService, *, hour: int = 16, minute: int = 30
) -> AsyncIOScheduler:
    """Return a scheduler with the daily OHLCV refresh job attached.

    Default run time is 16:30 IST (one hour after NSE close at 15:30).
    """
    scheduler = AsyncIOScheduler(timezone=IST)
    scheduler.add_job(
        refresh_all_symbols,
        trigger=CronTrigger(
            hour=hour, minute=minute, day_of_week="mon-fri", timezone=IST
        ),
        args=[service],
        id="data.refresh_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
