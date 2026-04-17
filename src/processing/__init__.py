"""Phase 2 — deterministic scoring and signal generation."""

from src.processing.features import InsufficientDataError, compute_features
from src.processing.scoring import (
    SCORING_VERSION,
    compose_score,
    compute_sub_scores,
    fundamental_sub_score,
    ma_sub_score,
    momentum_sub_score,
    support_resistance_sub_score,
    volatility_sub_score,
    volume_sub_score,
)
from src.processing.service import (
    DataSource,
    DefaultProcessingService,
    ProcessingError,
    ProcessingService,
)
from src.processing.signals import generate_signals

__all__ = [
    "SCORING_VERSION",
    "DataSource",
    "DefaultProcessingService",
    "InsufficientDataError",
    "ProcessingError",
    "ProcessingService",
    "compose_score",
    "compute_features",
    "compute_sub_scores",
    "fundamental_sub_score",
    "generate_signals",
    "ma_sub_score",
    "momentum_sub_score",
    "support_resistance_sub_score",
    "volatility_sub_score",
    "volume_sub_score",
]
