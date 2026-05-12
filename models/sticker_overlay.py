"""Sticker overlay model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.normalized_layout import DEFAULT_STICKER_WIDTH_RATIO, NormalizedLayoutEngine

from .overlay import OverlayBase


@dataclass(slots=True)
class StickerOverlay(OverlayBase):
    path: Path | None = None
    # Canonical sticker width ratio relative to output width. Values > 1 are
    # treated as legacy reference pixels and migrated at read time.
    scale: float = DEFAULT_STICKER_WIDTH_RATIO
    rotation: float = 0.0

    def effective_scale_ratio(self) -> float:
        return NormalizedLayoutEngine().normalize_width(self.scale)

    @property
    def active(self) -> bool:
        return self.enabled and self.path is not None
