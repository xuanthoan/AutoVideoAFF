"""Text overlay model."""
from __future__ import annotations

from dataclasses import dataclass

from core.normalized_layout import DEFAULT_FONT_RATIO, NormalizedLayoutEngine

from .overlay import OverlayBase


@dataclass(slots=True)
class TextOverlay(OverlayBase):
    text: str = ""
    template: str = "Orange White"
    # Legacy/reference control value kept for UI compatibility. The canonical
    # persisted text size is font_ratio relative to output video height.
    font_size: int = 96
    font_ratio: float = DEFAULT_FONT_RATIO

    def effective_font_ratio(self) -> float:
        # Auto-migrate legacy states that only changed font_size pixels.
        source = self.font_size if self.font_size != 96 and self.font_ratio == DEFAULT_FONT_RATIO else (self.font_ratio or self.font_size)
        return NormalizedLayoutEngine().normalize_font_size(source)

    def set_font_size(self, font_size: int) -> None:
        self.font_size = int(font_size)
        self.font_ratio = NormalizedLayoutEngine().normalize_font_size(self.font_size)

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.text.strip())
