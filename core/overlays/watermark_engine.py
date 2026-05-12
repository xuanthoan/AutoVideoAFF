"""Minimal-region text watermark renderer and FFmpeg overlay engine."""
from __future__ import annotations

import importlib.util
import math
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.normalized_layout import NormalizedLayoutEngine, REFERENCE_HEIGHT
from models.project_state import OverlaySettings
from models.watermark_overlay import WatermarkInstance, WatermarkOverlay
from utils.ffmpeg_helper import app_root

if importlib.util.find_spec("PySide6") is not None:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter
else:
    QRectF = Qt = QColor = QFont = QFontDatabase = QGuiApplication = QImage = QPainter = None


@dataclass(frozen=True, slots=True)
class WatermarkAvoidRegion:
    x: float
    y: float
    radius: float


class WatermarkLayoutEngine:
    """Create stable per-video watermark positions inside safe margins."""

    margin_x = 0.05
    margin_y = 0.05

    def generate(self, overlays: OverlaySettings, seed: int | None = None) -> list[WatermarkInstance]:
        watermark = overlays.watermark
        if not watermark.active:
            return []
        count = watermark.density_count
        rng = random.Random(seed)
        avoid = self._avoid_regions(overlays)
        if not watermark.random_position:
            return self._fixed_instances(watermark, count, rng)
        instances: list[WatermarkInstance] = []
        for index in range(count):
            instance = self._candidate(rng, watermark, count)
            attempts = 0
            while attempts < 80 and (self._too_close(instance, instances) or self._hits_avoid_region(instance, avoid)):
                instance = self._candidate(rng, watermark, count)
                attempts += 1
            instances.append(instance)
        return instances

    def _fixed_instances(self, watermark: WatermarkOverlay, count: int, rng: random.Random) -> list[WatermarkInstance]:
        base = watermark.instances[0] if watermark.instances else WatermarkInstance()
        if count == 1:
            return [WatermarkInstance(base.x, base.y, 0.0, 1.0, 1.0, 0.0, math.pi / 2, 1.0, 1.0)]
        anchors = [(0.24, 0.22), (0.76, 0.36), (0.30, 0.68), (0.72, 0.78), (0.50, 0.50), (0.18, 0.52), (0.82, 0.58)]
        return [
            WatermarkInstance(
                anchors[index % len(anchors)][0],
                anchors[index % len(anchors)][1],
                rng.uniform(-3.0, 3.0),
                self._scale_for_density(watermark.density, rng),
                self._opacity_multiplier_for_density(watermark.density, rng),
                rng.uniform(0.0, math.tau),
                rng.uniform(0.0, math.tau),
                rng.choice([-1.0, 1.0]),
                rng.choice([-1.0, 1.0]),
            )
            for index in range(count)
        ]

    def _candidate(self, rng: random.Random, watermark: WatermarkOverlay, count: int) -> WatermarkInstance:
        return WatermarkInstance(
            x=rng.uniform(self.margin_x, 1.0 - self.margin_x),
            y=rng.uniform(self.margin_y, 1.0 - self.margin_y),
            rotation=rng.uniform(-5.0, 5.0),
            scale=self._scale_for_density(watermark.density, rng),
            opacity_multiplier=self._opacity_multiplier_for_density(watermark.density, rng),
            phase_x=rng.uniform(0.0, math.tau),
            phase_y=rng.uniform(0.0, math.tau),
            direction_x=rng.choice([-1.0, 1.0]),
            direction_y=rng.choice([-1.0, 1.0]),
        )

    @staticmethod
    def _scale_for_density(density: str, rng: random.Random) -> float:
        if density == "single":
            return 1.0
        return rng.uniform(0.82, 1.08)

    @staticmethod
    def _opacity_multiplier_for_density(density: str, rng: random.Random) -> float:
        if density == "single":
            return 1.0
        if density == "multi-light":
            return rng.uniform(0.70, 0.86)
        if density == "multi-medium":
            return rng.uniform(0.50, 0.70)
        return rng.uniform(0.36, 0.55)

    @staticmethod
    def _too_close(candidate: WatermarkInstance, existing: list[WatermarkInstance]) -> bool:
        return any(abs(candidate.x - other.x) < 0.16 and abs(candidate.y - other.y) < 0.12 for other in existing)

    @staticmethod
    def _hits_avoid_region(candidate: WatermarkInstance, regions: list[WatermarkAvoidRegion]) -> bool:
        return any(math.hypot(candidate.x - region.x, candidate.y - region.y) < region.radius for region in regions)

    @staticmethod
    def _avoid_regions(overlays: OverlaySettings) -> list[WatermarkAvoidRegion]:
        regions: list[WatermarkAvoidRegion] = []
        for text_overlay in overlays.text_overlays():
            regions.append(WatermarkAvoidRegion(text_overlay.x, text_overlay.y, 0.18))
        for highlight_overlay in overlays.highlight_overlays():
            regions.append(WatermarkAvoidRegion(highlight_overlay.x, highlight_overlay.y, 0.18))
        for sticker_overlay in overlays.sticker_overlays():
            regions.append(WatermarkAvoidRegion(sticker_overlay.x, sticker_overlay.y, 0.14))
        return regions


class WatermarkTextRenderer:
    """Render plain watermark text into a transparent minimal bounding box."""

    FONT_FILES = ("Montserrat-ExtraBold.ttf", "Poppins-ExtraBold.ttf")
    _fonts_loaded = False
    _owned_app = None

    def __init__(self) -> None:
        self.layout = NormalizedLayoutEngine()

    def render_image(self, watermark: WatermarkOverlay, canvas_width: int, canvas_height: int):
        if QImage is None:
            raise RuntimeError("PySide6 is required to render watermark text assets.")
        self._ensure_qt_app()
        self._load_fonts()
        font_ratio = watermark.effective_font_ratio()
        scaled_font = max(8, self.layout.denormalize_font_size(font_ratio, canvas_height))
        font = QFont(watermark.font_family, scaled_font)
        font.setWeight(QFont.ExtraBold)
        font.setStyleStrategy(QFont.PreferAntialias)
        probe = QImage(8, 8, QImage.Format_ARGB32_Premultiplied)
        probe.fill(Qt.transparent)
        painter = QPainter(probe)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        lines = watermark.text.splitlines() or [watermark.text]
        line_spacing = round(scaled_font * 0.18)
        text_width = max(metrics.horizontalAdvance(line) for line in lines) if lines else 1
        text_height = len(lines) * metrics.height() + max(0, len(lines) - 1) * line_spacing
        pad = max(8, round(scaled_font * 0.35))
        image = QImage(text_width + pad * 2, text_height + pad * 2, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter.end()

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setFont(font)
        painter.setPen(QColor(watermark.font_color))
        y = pad
        for line in lines:
            painter.drawText(QRectF(pad, y, text_width, metrics.height()), Qt.AlignHCenter | Qt.AlignVCenter, line)
            y += metrics.height() + line_spacing
        painter.end()
        return image

    def render_png(self, path: Path, watermark: WatermarkOverlay, canvas_width: int, canvas_height: int) -> Path:
        image = self.render_image(watermark, canvas_width, canvas_height)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(path), "PNG"):
            raise RuntimeError(f"Unable to write watermark PNG: {path}")
        return path

    @classmethod
    def _ensure_qt_app(cls) -> None:
        if QGuiApplication.instance() is not None:
            return
        import os
        import sys

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._owned_app = QGuiApplication([sys.argv[0] or "AutoVideoAFF"])

    @classmethod
    def _load_fonts(cls) -> None:
        if cls._fonts_loaded:
            return
        font_dir = app_root() / "assets" / "fonts"
        for filename in cls.FONT_FILES:
            font_path = font_dir / filename
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
        cls._fonts_loaded = True


class WatermarkEngine:
    def __init__(self) -> None:
        self.renderer = WatermarkTextRenderer()
        self.layout = NormalizedLayoutEngine()
        self._asset_cache: dict[tuple[str, str, str, float, int, int], Path] = {}

    def render_asset(self, watermark: WatermarkOverlay, canvas_width: int, canvas_height: int, temp_files: list[Path] | None = None) -> Path:
        key = (watermark.text, watermark.font_family, watermark.font_color, round(watermark.effective_font_ratio(), 6), canvas_width, canvas_height)
        path = self._asset_cache.get(key)
        if path is None or not path.exists():
            path = self._new_asset_path()
            self.renderer.render_png(path, watermark, canvas_width, canvas_height)
            self._asset_cache[key] = path
        if temp_files is not None and path not in temp_files:
            temp_files.append(path)
        return path

    def build_filter(
        self,
        video_label: str,
        watermark_label: str,
        watermark: WatermarkOverlay,
        instance: WatermarkInstance,
        suffix: str = "",
    ) -> tuple[str, str]:
        out = f"watermark_v{suffix}"
        prepared = f"watermark_src{suffix}"
        opacity = min(max(watermark.opacity * instance.opacity_multiplier, 0.0), 1.0)
        rotation = watermark.rotation + instance.rotation
        scale = max(0.2, float(instance.scale))
        x = f"W*{instance.x:.4f}-w/2"
        y = f"H*{instance.y:.4f}-h/2"
        if watermark.slow_floating_motion:
            x = f"({x})+({8.0 / REFERENCE_HEIGHT:.8f}*H)*{instance.direction_x:.1f}*sin(t*0.2+{instance.phase_x:.4f})"
            y = f"({y})+({5.0 / REFERENCE_HEIGHT:.8f}*H)*{instance.direction_y:.1f}*cos(t*0.15+{instance.phase_y:.4f})"
        chain = (
            f"[{watermark_label}]scale=w='iw*{scale:.4f}':h='ih*{scale:.4f}':eval=frame,"
            f"format=rgba,colorchannelmixer=aa={opacity:.4f},"
            f"rotate='{rotation:.4f}*PI/180':ow=rotw(iw):oh=roth(ih):c=none[{prepared}];"
            f"[{video_label}][{prepared}]overlay=x='{x}':y='{y}':eval=frame[{out}]"
        )
        return chain, out

    @staticmethod
    def _new_asset_path() -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="autovideoaff_watermark_", suffix=".png", delete=False)
        path = Path(handle.name)
        handle.close()
        return path
