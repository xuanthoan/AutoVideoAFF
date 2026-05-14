"""Text watermark overlay model for anti-reupload branding."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.normalized_layout import NormalizedLayoutEngine

WatermarkDensity = Literal["single", "multi-light", "multi-medium", "multi-heavy"]

DEFAULT_WATERMARK_FONT_RATIO = 44 / 1920
WATERMARK_DENSITY_COUNTS: dict[str, int] = {
    "single": 1,
    "multi-light": 2,
    "multi-medium": 4,
    "multi-heavy": 7,
}
WATERMARK_FONTS = ["Montserrat", "Poppins", "Arial", "Helvetica", "Times New Roman"]
WATERMARK_COLORS = ["#FFFFFF", "#F5F5F5", "#111111", "#FFD966", "#B9FFFC"]


@dataclass(slots=True)
class WatermarkInstance:
    x: float = 0.5
    y: float = 0.5
    rotation: float = 0.0
    scale: float = 1.0
    opacity_multiplier: float = 1.0
    phase_x: float = 0.0
    phase_y: float = 0.0
    direction_x: float = 1.0
    direction_y: float = 1.0


@dataclass(slots=True)
class WatermarkOverlay:
    enabled: bool = False
    text: str = ""
    font_family: str = "Montserrat"
    font_size: int = 44
    font_ratio: float = DEFAULT_WATERMARK_FONT_RATIO
    font_color: str = "#FFFFFF"
    opacity_percent: int = 15
    rotation: float = -15.0
    random_position: bool = True
    slow_floating_motion: bool = True
    density: WatermarkDensity = "multi-light"
    instances: list[WatermarkInstance] = field(default_factory=lambda: [WatermarkInstance(0.38, 0.38, 0.0), WatermarkInstance(0.62, 0.62, 0.0)])

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.text.strip())

    @property
    def opacity(self) -> float:
        return min(max(float(self.opacity_percent) / 100.0, 0.0), 1.0)

    @property
    def density_count(self) -> int:
        return WATERMARK_DENSITY_COUNTS.get(self.density, 1)

    def effective_font_ratio(self) -> float:
        source = self.font_size if self.font_size != 44 and self.font_ratio == DEFAULT_WATERMARK_FONT_RATIO else (self.font_ratio or self.font_size)
        return NormalizedLayoutEngine().normalize_font_size(source)

    def set_font_size(self, font_size: int) -> None:
        self.font_size = int(font_size)
        self.font_ratio = NormalizedLayoutEngine().normalize_font_size(self.font_size)
