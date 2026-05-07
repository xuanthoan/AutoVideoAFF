"""Shared overlay data models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal


class MotionPreset(str, Enum):
    NONE = "None"
    FADE_IN = "Fade In"
    FADE_OUT = "Fade Out"
    BOUNCE = "Bounce"
    POP = "Pop"
    SLIDE_UP = "Slide Up"
    SLIDE_DOWN = "Slide Down"
    SCALE = "Scale"
    DRIFT = "Drift"
    # Backward-compatible aliases for older project states/UI values.
    FADE = "Fade"
    SLIDE = "Slide"
    ZOOM = "Zoom"
    ELASTIC = "Elastic"

    @classmethod
    def from_label(cls, label: str) -> "MotionPreset":
        for preset in cls:
            if preset.value == label:
                return preset
        return cls.NONE


@dataclass(slots=True)
class OverlayBase:
    enabled: bool = True
    x: float = 0.5
    y: float = 0.5
    duration: float = 3.0
    start_time: float = 0.0
    motion: MotionPreset = MotionPreset.NONE

    def clamp_to_safe_area(self, width: int, height: int) -> None:
        left = width * 0.05
        right = width - width * 0.05
        top = height * 0.08
        bottom = height - height * 0.16
        self.x = min(max(self.x * width, left), right) / width
        self.y = min(max(self.y * height, top), bottom) / height


CropFocus = Literal["top", "center", "bottom"]


@dataclass(slots=True)
class StickerAsset:
    path: Path
    scale: float = 1.0
    rotation: float = 0.0
