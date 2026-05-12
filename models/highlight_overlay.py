"""Smart sales highlight overlay model."""
from __future__ import annotations

from dataclasses import dataclass

from core.normalized_layout import NormalizedLayoutEngine
from core.overlays.highlight_library import HighlightStyleManager

from .overlay import MotionPreset, OverlayBase

DEFAULT_HIGHLIGHT_FONT_RATIO = 118 / 1920


@dataclass(slots=True)
class HighlightOverlay(OverlayBase):
    text: str = ""
    style: str = "TikTok Bold"
    font_size: int = 118
    font_ratio: float = DEFAULT_HIGHLIGHT_FONT_RATIO

    def effective_font_ratio(self) -> float:
        source = self.font_size if self.font_size != 118 and self.font_ratio == DEFAULT_HIGHLIGHT_FONT_RATIO else (self.font_ratio or self.font_size)
        return NormalizedLayoutEngine().normalize_font_size(source)

    def set_font_size(self, font_size: int) -> None:
        self.font_size = int(font_size)
        self.font_ratio = NormalizedLayoutEngine().normalize_font_size(self.font_size)

    def set_animation_label(self, label: str) -> None:
        self.motion = MotionPreset.from_label(label)

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.text.strip())

    @property
    def style_manager(self) -> HighlightStyleManager:
        return HighlightStyleManager()
