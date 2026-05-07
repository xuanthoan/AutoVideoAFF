"""Template-based typography scaling."""
from __future__ import annotations

REFERENCE_HEIGHT = 1920


class TypographyEngine:
    def scale_factor(self, video_height: int) -> float:
        return video_height / REFERENCE_HEIGHT

    def scale(self, value: float, video_height: int) -> int:
        return round(value * self.scale_factor(video_height))
