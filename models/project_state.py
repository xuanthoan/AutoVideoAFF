"""Serializable project state for the all-in-one production workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from .highlight_overlay import HighlightOverlay
from .overlay import CropFocus
from .sticker_overlay import StickerOverlay
from .text_overlay import TextOverlay
from .watermark_overlay import WatermarkOverlay

AspectRatio = Literal["9:16", "1:1", "16:9"]
FadeCurve = Literal["linear", "smooth", "strong"]


PlatformPreset = Literal["TikTok", "Instagram Reels", "YouTube Shorts", "Custom"]

SegmentSource = Literal["auto", "manual"]


@dataclass(slots=True)
class TimelineSegment:
    start_time: float
    end_time: float
    source: SegmentSource = "auto"
    enabled: bool = True
    locked: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def normalized(self, video_duration: float | None = None) -> "TimelineSegment":
        start = max(0.0, float(self.start_time))
        end_limit = float(video_duration) if video_duration is not None else None
        end = max(start + 0.05, float(self.end_time))
        if end_limit is not None:
            end = min(end, max(start + 0.05, end_limit))
        return TimelineSegment(start, end, self.source, bool(self.enabled), bool(self.locked))

    def to_json(self) -> dict:
        return {
            "start": round(float(self.start_time), 3),
            "end": round(float(self.end_time), 3),
            "source": self.source,
            "enabled": bool(self.enabled),
            "locked": bool(self.locked),
        }

    @classmethod
    def from_json(cls, data: dict, default_source: SegmentSource = "manual") -> "TimelineSegment":
        return cls(
            start_time=float(data.get("start", data.get("start_time", 0.0))),
            end_time=float(data.get("end", data.get("end_time", 0.0))),
            source=data.get("source", default_source),
            enabled=bool(data.get("enabled", True)),
            locked=bool(data.get("locked", False)),
        )


class WorkflowMode(str, Enum):
    PIPELINE_1 = "Pipeline 1 — Shuffle + Image"
    PIPELINE_2 = "Pipeline 2 — Shuffle + Image + Overlay"
    PIPELINE_3 = "Pipeline 3 — Shuffle + Overlay"
    PIPELINE_4 = "Pipeline 4 — Overlay Only"


@dataclass(slots=True)
class SceneShuffleSettings:
    enabled: bool = True
    sensitivity: float = 30.0
    random_mode: bool = True
    keep_first_segment: bool = True
    fallback_min_seconds: float = 3.0
    fallback_max_seconds: float = 5.0
    auto_segments: list[TimelineSegment] = field(default_factory=list)
    manual_segments: list[TimelineSegment] = field(default_factory=list)
    segment_video_path: str | None = None

    @property
    def manual_mode(self) -> bool:
        return len(self.manual_segments) > 0

    def active_segments(self) -> list[TimelineSegment]:
        return self.manual_segments if self.manual_mode else self.auto_segments


@dataclass(slots=True)
class ImageCompositeSettings:
    enabled: bool = False
    image_pool: list[Path] = field(default_factory=list)
    image_height_percent: float = 35.0
    overlap_percent: float = 5.0
    crop_focus: CropFocus = "center"
    fade_curve: FadeCurve = "linear"
    auto_random_image: bool = True


@dataclass(slots=True)
class OverlaySettings:
    watermark_enabled: bool = False
    text_enabled: bool = False
    highlight_enabled: bool = False
    sticker_enabled: bool = False
    watermark: WatermarkOverlay = field(default_factory=WatermarkOverlay)
    text: TextOverlay = field(default_factory=TextOverlay)
    highlight: HighlightOverlay = field(default_factory=HighlightOverlay)
    sticker: StickerOverlay = field(default_factory=StickerOverlay)
    text_layers: list[TextOverlay] = field(default_factory=list)
    highlight_layers: list[HighlightOverlay] = field(default_factory=list)
    sticker_layers: list[StickerOverlay] = field(default_factory=list)

    def watermark_overlays(self) -> list[WatermarkOverlay]:
        return [self.watermark] if self.watermark_enabled and self.watermark.active else []

    def text_overlays(self) -> list[TextOverlay]:
        layers = [overlay for overlay in self.text_layers if overlay.active]
        if self.text_enabled and self.text.active and self.text not in layers:
            layers.insert(0, self.text)
        return layers[:20]

    def highlight_overlays(self) -> list[HighlightOverlay]:
        layers = [overlay for overlay in self.highlight_layers if overlay.active]
        if self.highlight_enabled and self.highlight.active and self.highlight not in layers:
            layers.insert(0, self.highlight)
        return layers[:20]

    def sticker_overlays(self) -> list[StickerOverlay]:
        layers = [overlay for overlay in self.sticker_layers if overlay.active]
        if self.sticker_enabled and self.sticker.active and self.sticker not in layers:
            layers.insert(0, self.sticker)
        return layers[:20]

    @property
    def enabled(self) -> bool:
        return bool(self.watermark_overlays() or self.text_overlays() or self.highlight_overlays() or self.sticker_overlays())


@dataclass(slots=True)
class ExportSettings:
    output_dir: Path = Path("output")
    aspect_ratio: AspectRatio = "9:16"
    crf: int = 18
    preset: str = "veryfast"
    auto_open_output: bool = False
    developer_mode: bool = False


@dataclass(slots=True)
class SafeAreaSettings:
    platform: PlatformPreset = "TikTok"
    enabled: bool = True
    snap_enabled: bool = True


@dataclass(slots=True)
class ProjectState:
    videos: list[Path] = field(default_factory=list)
    workflow_mode: WorkflowMode = WorkflowMode.PIPELINE_1
    scene_shuffle: SceneShuffleSettings = field(default_factory=SceneShuffleSettings)
    image_composite: ImageCompositeSettings = field(default_factory=ImageCompositeSettings)
    overlays: OverlaySettings = field(default_factory=OverlaySettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    safe_area: SafeAreaSettings = field(default_factory=SafeAreaSettings)

    def render_count_label(self) -> str:
        return f"Render Video ({len(self.videos)})" if self.videos else "Render Video"
