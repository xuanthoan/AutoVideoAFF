"""Normalized resolution helpers for preview/export overlay parity.

All persisted overlay geometry should be ratios. Legacy pixel-like values are
converted against a single reference canvas so 720p, 1080p, 1440p, and 4K
renders keep the same visual proportions.
"""
from __future__ import annotations

from dataclasses import dataclass


REFERENCE_WIDTH = 1080
REFERENCE_HEIGHT = 1920
DEFAULT_FONT_RATIO = 96 / REFERENCE_HEIGHT
DEFAULT_STICKER_WIDTH_RATIO = 0.16


@dataclass(frozen=True, slots=True)
class NormalizedLayoutEngine:
    """Convert overlay positions, typography, sticker size, and motion offsets."""

    reference_width: int = REFERENCE_WIDTH
    reference_height: int = REFERENCE_HEIGHT

    @staticmethod
    def clamp_ratio(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return min(max(float(value), minimum), maximum)

    def normalize_position(self, x: float, y: float, width: int, height: int) -> tuple[float, float]:
        return self.clamp_ratio(float(x) / max(width, 1)), self.clamp_ratio(float(y) / max(height, 1))

    def denormalize_position(self, x_ratio: float, y_ratio: float, width: int, height: int) -> tuple[float, float]:
        return self.clamp_ratio(x_ratio) * width, self.clamp_ratio(y_ratio) * height

    def normalize_font_size(self, font_size: float, reference_height: int | None = None) -> float:
        """Return a font-height ratio, migrating legacy reference-pixel values."""
        value = float(font_size)
        if value <= 1.0:
            return self.clamp_ratio(value, 0.001, 1.0)
        return self.clamp_ratio(value / float(reference_height or self.reference_height), 0.001, 1.0)

    def denormalize_font_size(self, font_ratio: float, output_height: int) -> int:
        return max(1, round(self.normalize_font_size(font_ratio) * max(output_height, 1)))

    def normalize_width(self, width: float, reference_width: int | None = None) -> float:
        value = float(width)
        if value <= 1.0:
            return self.clamp_ratio(value, 0.001, 1.0)
        return self.clamp_ratio(value / float(reference_width or self.reference_width), 0.001, 1.0)

    def denormalize_width(self, width_ratio: float, output_width: int) -> int:
        return max(1, round(self.normalize_width(width_ratio) * max(output_width, 1)))

    def normalize_height(self, height: float, reference_height: int | None = None) -> float:
        value = float(height)
        if value <= 1.0:
            return self.clamp_ratio(value, 0.001, 1.0)
        return self.clamp_ratio(value / float(reference_height or self.reference_height), 0.001, 1.0)

    def denormalize_height(self, height_ratio: float, output_height: int) -> int:
        return max(1, round(self.normalize_height(height_ratio) * max(output_height, 1)))

    def normalize_motion_amplitude(self, pixels: float, axis_size: int | None = None) -> float:
        return float(pixels) / float(axis_size or self.reference_height)

    def denormalize_motion_amplitude(self, ratio: float, axis_size: float) -> float:
        return float(ratio) * float(axis_size)

    def debug_font(self, font_ratio: float, output_height: int) -> str:
        computed = self.denormalize_font_size(font_ratio, output_height)
        return f"[NORMALIZED] font_ratio={font_ratio:.4f} output_height={output_height} computed_font_size={computed}"

    def debug_sticker(self, width_ratio: float, output_width: int) -> str:
        computed = self.denormalize_width(width_ratio, output_width)
        return f"[NORMALIZED] sticker_width_ratio={width_ratio:.4f} output_width={output_width} computed_sticker_width={computed}"
