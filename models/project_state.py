"""Serializable project state for the all-in-one production workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .overlay import CropFocus
from .sticker_overlay import StickerOverlay
from .text_overlay import TextOverlay

AspectRatio = Literal["9:16", "1:1", "16:9"]


@dataclass(slots=True)
class SceneShuffleSettings:
    enabled: bool = True
    sensitivity: float = 30.0
    random_mode: bool = True
    keep_first_segment: bool = True
    fallback_min_seconds: float = 3.0
    fallback_max_seconds: float = 5.0


@dataclass(slots=True)
class ImageCompositeSettings:
    enabled: bool = False
    image_pool: list[Path] = field(default_factory=list)
    image_height_percent: float = 35.0
    overlap_percent: float = 5.0
    crop_focus: CropFocus = "center"
    auto_random_image: bool = True


@dataclass(slots=True)
class OverlaySettings:
    text_enabled: bool = False
    sticker_enabled: bool = False
    text: TextOverlay = field(default_factory=TextOverlay)
    sticker: StickerOverlay = field(default_factory=StickerOverlay)

    @property
    def enabled(self) -> bool:
        return (self.text_enabled and self.text.active) or (self.sticker_enabled and self.sticker.active)


@dataclass(slots=True)
class ExportSettings:
    output_dir: Path = Path("output")
    aspect_ratio: AspectRatio = "9:16"
    crf: int = 18
    preset: str = "veryfast"


@dataclass(slots=True)
class ProjectState:
    videos: list[Path] = field(default_factory=list)
    scene_shuffle: SceneShuffleSettings = field(default_factory=SceneShuffleSettings)
    image_composite: ImageCompositeSettings = field(default_factory=ImageCompositeSettings)
    overlays: OverlaySettings = field(default_factory=OverlaySettings)
    export: ExportSettings = field(default_factory=ExportSettings)

    def render_count_label(self) -> str:
        return f"Xuất Video ({len(self.videos)})" if self.videos else "Xuất Video"
