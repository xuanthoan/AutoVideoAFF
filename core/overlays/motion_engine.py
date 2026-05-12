"""Compatibility wrapper for the shared overlay motion engine."""
from __future__ import annotations

from core.motion_engine import (
    FFmpegExpressionBuilder,
    MotionEngine,
    MotionEvaluator,
    MotionSpec,
    OverlayAnimation,
    PreviewTransform,
    PreviewTransformEvaluator,
)

__all__ = [
    "FFmpegExpressionBuilder",
    "MotionEngine",
    "MotionEvaluator",
    "MotionSpec",
    "OverlayAnimation",
    "PreviewTransform",
    "PreviewTransformEvaluator",
]
