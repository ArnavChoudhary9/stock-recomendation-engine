"""API v1 routers."""

from src.api.routers.analysis import router as analysis_router
from src.api.routers.chat import router as chat_router
from src.api.routers.news import router as news_router
from src.api.routers.portfolio import kite_router, portfolio_router
from src.api.routers.reports import router as reports_router
from src.api.routers.stocks import router as stocks_router
from src.api.routers.system import router as system_router
from src.api.routers.watchlist import router as watchlist_router

__all__ = [
    "analysis_router",
    "chat_router",
    "kite_router",
    "news_router",
    "portfolio_router",
    "reports_router",
    "stocks_router",
    "system_router",
    "watchlist_router",
]
