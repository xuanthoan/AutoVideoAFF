"""Realtime preview canvas with safe-area, live overlays, and snap guides."""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

from core.overlays.highlight_library import HighlightStyleManager
from core.overlays.template_manager import TemplateManager
from core.overlays.motion_engine import MotionEngine
from core.overlays.transform import OverlayTransform
from core.overlays.typography_engine import SocialTypographyRenderer
from core.overlays.watermark_engine import WatermarkTextRenderer
from core.safe_area_engine import NormalizedRect, SafeAreaEngine
from models.watermark_overlay import WatermarkOverlay

try:
    from PySide6.QtCore import QPointF, QRectF, Qt, Signal
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QLabel
except ImportError:  # lets non-GUI CI import architecture modules without PySide6 installed
    QPointF = QRectF = Qt = Signal = QColor = QPainter = QPen = QPixmap = QLabel = None


if QLabel:
    class PreviewCanvas(QLabel):
        overlayMoved = Signal(str, float, float)
        previewMotionDebug = Signal(str)
        SNAP_THRESHOLD = 10

        def __init__(self) -> None:
            super().__init__("Preview")
            self.setMinimumSize(420, 560)
            self.setAlignment(Qt.AlignCenter)
            self.setMouseTracking(True)
            self.setStyleSheet("background:#111;color:#aaa;border:1px solid #333;")
            self._snap_x: int | None = None
            self._snap_y: int | None = None
            self._source_pixmap: QPixmap | None = None
            self._safe_area_engine = SafeAreaEngine()
            self._safe_area_platform = "TikTok"
            self._safe_area_enabled = True
            self._snap_enabled = True
            self._template_manager = TemplateManager()
            self._highlight_style_manager = HighlightStyleManager()
            self._typography_renderer = SocialTypographyRenderer()
            self._watermark_renderer = WatermarkTextRenderer()
            self._motion_engine = MotionEngine()
            self._current_time = 0.0
            self._text_pixmap_cache_key = None
            self._text_pixmap_cache = None
            self._highlight_pixmap_cache_key = None
            self._highlight_pixmap_cache = None
            self._watermark_pixmap_cache_key = None
            self._watermark_pixmap_cache = None
            self._typography_pixmap_cache = {}
            self._selected_highlight_key: str | None = None
            self._last_motion_debug: dict[str, float] = {}
            self._overlays = {
                "watermark": {"active": False, "x": 0.5, "y": 0.5, "w": 160, "h": 48, "text": "", "font_family": "Montserrat", "font_size": 44/1920, "font_color": "#FFFFFF", "opacity": 0.15, "rotation": -15.0, "slow_floating_motion": True, "instances": []},
                "text": {"active": False, "x": 0.5, "y": 0.35, "w": 260, "h": 90, "text": "", "template": "Orange White", "font_size": 96, "motion": "None", "motion_speed": 1.0, "motion_strength": 1.0, "start": 0.0, "end": 3.0},
                "highlight": {"active": False, "x": 0.5, "y": 0.25, "w": 280, "h": 96, "text": "", "template": "TikTok Bold", "font_size": 118/1920, "motion": "Pop", "motion_speed": 1.25, "motion_strength": 1.35, "start": 0.0, "end": 3.0},
                "sticker": {"active": False, "x": 0.5, "y": 0.55, "w": 120, "h": 120, "pixmap": None, "scale": 0.16, "rotation": 0.0, "motion": "None", "motion_speed": 1.0, "motion_strength": 1.0, "start": 0.0, "end": 3.0},
            }
            self._drag_kind: str | None = None

        def set_safe_area_options(self, platform: str = "TikTok", enabled: bool = True, snap_enabled: bool = True) -> None:
            self._safe_area_platform = platform
            self._safe_area_enabled = enabled
            self._snap_enabled = snap_enabled
            self.update()

        def set_preview_image(self, image_path: Path) -> None:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                self.setText("Preview unavailable")
                self._source_pixmap = None
            else:
                self.setText("")
                self._source_pixmap = pixmap
                self._apply_scaled_pixmap()
            self.update()

        def set_watermark_overlay(
            self,
            watermark,
            active: bool,
        ) -> None:
            data = self._overlays["watermark"]
            data.update({
                "text": watermark.text,
                "font_family": watermark.font_family,
                "font_size": watermark.effective_font_ratio(),
                "font_color": watermark.font_color,
                "opacity": watermark.opacity,
                "rotation": watermark.rotation,
                "slow_floating_motion": watermark.slow_floating_motion,
                "instances": list(watermark.instances),
                "active": active,
            })
            self.update()

        def set_text_overlay(
            self,
            text: str,
            template: str,
            font_size: int,
            active: bool,
            motion: str = "None",
            motion_speed: float = 1.0,
            motion_strength: float = 1.0,
        ) -> None:
            data = self._overlays["text"]
            data.update({
                "text": text,
                "template": template,
                "font_size": font_size,
                "active": active,
                "motion": motion,
                "motion_speed": motion_speed,
                "motion_strength": motion_strength,
            })
            self.update()

        def set_highlight_overlay(
            self,
            text: str,
            style: str,
            font_size: float,
            active: bool,
            motion: str = "Pop",
            motion_speed: float = 1.25,
            motion_strength: float = 1.35,
        ) -> None:
            data = self._overlays["highlight"]
            data.update({
                "text": text,
                "template": style,
                "font_size": font_size,
                "active": active,
                "motion": motion,
                "motion_speed": motion_speed,
                "motion_strength": motion_strength,
            })
            self.update()

        def set_highlight_layers(self, layers: list[dict], selected_key: str | None = None) -> None:
            for key in [key for key in self._overlays if key.startswith("highlight_")]:
                self._overlays.pop(key, None)
            self._selected_highlight_key = selected_key
            for index, layer in enumerate(layers, start=1):
                key = str(layer.get("key", f"highlight_{index}"))
                self._overlays[key] = {
                    "active": layer.get("active", False),
                    "x": layer.get("x", 0.5),
                    "y": layer.get("y", 0.25),
                    "w": 280,
                    "h": 96,
                    "text": layer.get("text", ""),
                    "template": layer.get("style", "TikTok Bold"),
                    "font_size": layer.get("font_size", 118 / 1920),
                    "motion": layer.get("motion", "Pop"),
                    "motion_speed": layer.get("motion_speed", 1.25),
                    "motion_strength": layer.get("motion_strength", 1.35),
                    "start": layer.get("start", 0.0),
                    "end": layer.get("end", 3.0),
                }
            self.update()

        def set_sticker_overlay(
            self,
            path: Path | None,
            scale: float,
            rotation: float,
            active: bool,
            motion: str = "None",
            motion_speed: float = 1.0,
            motion_strength: float = 1.0,
        ) -> None:
            data = self._overlays["sticker"]
            pixmap = data.get("pixmap")
            if path is not None and (data.get("path") != path or pixmap is None):
                pixmap = QPixmap(str(path))
                data["path"] = path
            data.update({
                "pixmap": pixmap,
                "scale": scale,
                "rotation": rotation,
                "motion": motion,
                "motion_speed": motion_speed,
                "motion_strength": motion_strength,
                "active": active and pixmap is not None and not pixmap.isNull(),
            })
            self.update()

        def set_playhead_time(self, time_seconds: float) -> None:
            self._current_time = max(0.0, float(time_seconds))
            self.update()

        def set_overlay_timing(self, kind: str, start: float, end: float) -> None:
            if kind in self._overlays:
                self._overlays[kind]["start"] = max(0.0, float(start))
                self._overlays[kind]["end"] = max(float(end), float(start) + 0.1)
                self.update()

        def set_overlay_active(self, kind: str, active: bool) -> None:
            if kind in self._overlays:
                self._overlays[kind]["active"] = active
                self.update()

        def set_overlay_position(self, kind: str, x: float, y: float) -> None:
            if kind in self._overlays:
                self._overlays[kind]["x"] = min(max(x, 0.0), 1.0)
                self._overlays[kind]["y"] = min(max(y, 0.0), 1.0)
                self.update()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._apply_scaled_pixmap()

        def mousePressEvent(self, event):
            if event.button() != Qt.LeftButton:
                return super().mousePressEvent(event)
            highlight_keys = [key for key in self._overlays if key.startswith("highlight_")]
            for kind in ("sticker", *highlight_keys, "highlight", "text"):
                if self._overlay_rect(kind).contains(event.position()):
                    self._drag_kind = kind
                    return
            return super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if not self._drag_kind:
                return super().mouseMoveEvent(event)
            x = event.position().x()
            y = event.position().y()
            canvas = self._canvas_rect()
            center_x = canvas.center().x()
            center_y = canvas.center().y()
            self._snap_x = None
            self._snap_y = None
            if self._snap_enabled and abs(x - center_x) <= self.SNAP_THRESHOLD:
                x = center_x
                self._snap_x = int(center_x)
            if self._snap_enabled and abs(y - center_y) <= self.SNAP_THRESHOLD:
                y = center_y
                self._snap_y = int(center_y)
            norm_x = min(max((x - canvas.left()) / max(canvas.width(), 1), 0.0), 1.0)
            norm_y = min(max((y - canvas.top()) / max(canvas.height(), 1), 0.0), 1.0)
            norm_x, norm_y = self._clamp_to_safe_area(self._drag_kind, norm_x, norm_y)
            self.set_overlay_position(self._drag_kind, norm_x, norm_y)
            self.overlayMoved.emit(self._drag_kind, norm_x, norm_y)

        def mouseReleaseEvent(self, event):
            self._drag_kind = None
            self._snap_x = None
            self._snap_y = None
            self.update()
            return super().mouseReleaseEvent(event)

        def _apply_scaled_pixmap(self) -> None:
            if self._source_pixmap is None or self._source_pixmap.isNull():
                return
            scaled = self._source_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            if self._safe_area_enabled:
                self._draw_safe_area(painter)
            self._draw_watermark_overlay(painter)
            self._draw_text_overlay(painter)
            self._draw_highlight_overlay(painter)
            self._draw_sticker_overlay(painter)
            guide_pen = QPen(QColor(90, 190, 255, 170), 2)
            painter.setPen(guide_pen)
            if self._snap_x is not None:
                painter.drawLine(self._snap_x, 0, self._snap_x, self.height())
            if self._snap_y is not None:
                painter.drawLine(0, self._snap_y, self.width(), self._snap_y)

        def _draw_watermark_overlay(self, painter: QPainter) -> None:
            data = self._overlays["watermark"]
            if not data.get("active") or not str(data.get("text", "")).strip():
                return
            canvas = self._canvas_rect()
            key = (
                str(data["text"]),
                str(data["font_family"]),
                str(data["font_color"]),
                float(data["font_size"]),
                round(canvas.width()),
                round(canvas.height()),
            )
            if key != self._watermark_pixmap_cache_key or self._watermark_pixmap_cache is None:
                preview_watermark = WatermarkOverlay(
                    text=str(data["text"]),
                    font_family=str(data["font_family"]),
                    font_ratio=float(data["font_size"]),
                    font_color=str(data["font_color"]),
                )
                image = self._watermark_renderer.render_image(preview_watermark, round(canvas.width()), round(canvas.height()))
                self._watermark_pixmap_cache = QPixmap.fromImage(image)
                self._watermark_pixmap_cache_key = key
            pixmap = self._watermark_pixmap_cache
            data["w"] = pixmap.width()
            data["h"] = pixmap.height()
            for index, instance in enumerate(data.get("instances", []), start=1):
                scaled = pixmap.scaled(
                    max(1, round(pixmap.width() * max(0.2, float(instance.scale)))),
                    max(1, round(pixmap.height() * max(0.2, float(instance.scale)))),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x_offset = y_offset = 0.0
                if data.get("slow_floating_motion", True):
                    x_offset = (8.0 / 1920.0) * canvas.height() * float(instance.direction_x) * math.sin(self._current_time * 0.2 + float(instance.phase_x))
                    y_offset = (5.0 / 1920.0) * canvas.height() * float(instance.direction_y) * math.cos(self._current_time * 0.15 + float(instance.phase_y))
                center = QPointF(
                    canvas.left() + float(instance.x) * canvas.width() + x_offset,
                    canvas.top() + float(instance.y) * canvas.height() + y_offset,
                )
                painter.save()
                painter.translate(center)
                painter.rotate(float(data["rotation"]) + float(instance.rotation))
                painter.setOpacity(min(max(float(data["opacity"]) * float(instance.opacity_multiplier), 0.0), 1.0))
                painter.drawPixmap(QPointF(-scaled.width() / 2, -scaled.height() / 2), scaled)
                painter.restore()
                if index == 1:
                    self._emit_motion_debug("watermark", {"motion": "Slow Floating" if data.get("slow_floating_motion", True) else "None", "x": instance.x, "y": instance.y}, SimpleNamespace(x_offset=x_offset, y_offset=y_offset, scale=instance.scale, opacity=float(data["opacity"]) * float(instance.opacity_multiplier), rotation_delta=instance.rotation))

        def _draw_text_overlay(self, painter: QPainter) -> None:
            self._draw_typography_data(painter, "text", self._overlays["text"], self._template_manager)

        def _draw_highlight_overlay(self, painter: QPainter) -> None:
            highlight_keys = [key for key in self._overlays if key.startswith("highlight_")]
            if highlight_keys:
                for key in highlight_keys:
                    self._draw_typography_data(painter, key, self._overlays[key], self._highlight_style_manager)
            else:
                self._draw_typography_data(painter, "highlight", self._overlays["highlight"], self._highlight_style_manager)

        def _draw_typography_data(self, painter: QPainter, kind: str, data: dict, template_manager) -> None:
            if not self._overlay_visible(data) or not str(data["text"]).strip():
                return
            template = template_manager.get(str(data["template"]))
            canvas = self._canvas_rect()
            key = (kind, str(data["text"]), str(data["template"]), float(data["font_size"]), round(canvas.width()), round(canvas.height()))
            pixmap = self._typography_pixmap_cache.get(key)
            if pixmap is None:
                image = self._typography_renderer.render_image(
                    str(data["text"]),
                    template,
                    float(data["font_size"]),
                    round(canvas.width()),
                    round(canvas.height()),
                )
                pixmap = QPixmap.fromImage(image)
                self._typography_pixmap_cache[key] = pixmap
            data["w"] = pixmap.width()
            data["h"] = pixmap.height()
            transformed, transform = self._preview_transform(data, pixmap, canvas)
            center = QPointF(
                canvas.left() + float(data["x"]) * canvas.width() + transform.x_offset,
                canvas.top() + float(data["y"]) * canvas.height() + transform.y_offset,
            )
            painter.save()
            painter.setOpacity(transform.opacity)
            painter.drawPixmap(QPointF(center.x() - transformed.width() / 2, center.y() - transformed.height() / 2), transformed)
            if kind == self._selected_highlight_key:
                painter.setOpacity(1.0)
                painter.setPen(QPen(QColor(255, 220, 80, 210), 2, Qt.DashLine))
                painter.drawRect(QRectF(center.x() - transformed.width() / 2, center.y() - transformed.height() / 2, transformed.width(), transformed.height()))
            painter.restore()
            self._emit_motion_debug(kind, data, transform)

        def _draw_sticker_overlay(self, painter: QPainter) -> None:
            data = self._overlays["sticker"]
            pixmap = data.get("pixmap")
            if not self._overlay_visible(data) or pixmap is None or pixmap.isNull():
                return
            canvas = self._canvas_rect()
            target_width = OverlayTransform(
                x=float(data["x"]),
                y=float(data["y"]),
                scale_ratio=float(data["scale"]),
                rotation=float(data["rotation"]),
            ).sticker_width_pixels(round(canvas.width()))
            scaled = pixmap.scaled(target_width, target_width, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled, transform = self._preview_transform(data, scaled, canvas)
            data["w"] = scaled.width()
            data["h"] = scaled.height()
            rect = self._overlay_rect("sticker")
            painter.save()
            center = QPointF(rect.center().x() + transform.x_offset, rect.center().y() + transform.y_offset)
            painter.translate(center)
            painter.rotate(float(data["rotation"]) + transform.rotation_delta)
            painter.setOpacity(transform.opacity)
            painter.drawPixmap(QPointF(-scaled.width() / 2, -scaled.height() / 2), scaled)
            painter.restore()
            self._emit_motion_debug("sticker", data, transform)

        def _draw_safe_area(self, painter: QPainter) -> None:
            text_rect = self._safe_rect("text")
            sticker_rect = self._safe_rect("sticker")
            painter.fillRect(QRectF(0, 0, self.width(), text_rect.top()), QColor(0, 0, 0, 55))
            painter.fillRect(QRectF(0, text_rect.bottom(), self.width(), self.height() - text_rect.bottom()), QColor(0, 0, 0, 55))
            painter.fillRect(QRectF(0, text_rect.top(), text_rect.left(), text_rect.height()), QColor(0, 0, 0, 45))
            painter.fillRect(QRectF(text_rect.right(), text_rect.top(), self.width() - text_rect.right(), text_rect.height()), QColor(0, 0, 0, 45))
            painter.setPen(QPen(QColor(90, 220, 120, 180), 2, Qt.DashLine))
            painter.drawRoundedRect(text_rect, 8, 8)
            painter.setPen(QPen(QColor(120, 220, 255, 100), 1, Qt.DotLine))
            painter.drawRoundedRect(sticker_rect, 8, 8)
            painter.setPen(QPen(QColor(255, 90, 90, 70), 1, Qt.DotLine))
            for zone in self._safe_area_engine.calculate(self.width(), self.height(), platform=self._safe_area_platform).ui_exclusion_zones:
                painter.drawRect(self._rect_from_normalized(zone))

        def _preview_transform(self, data: dict, pixmap: QPixmap, canvas: QRectF):
            transform = self._motion_engine.preview_transform(
                str(data.get("motion", "None")),
                self._current_time,
                float(data.get("start", 0.0)),
                float(data.get("end", 0.0)),
                canvas.width(),
                canvas.height(),
                pixmap.width(),
                pixmap.height(),
                float(data.get("x", 0.5)),
                float(data.get("y", 0.5)),
                float(data.get("motion_speed", 1.0)),
                float(data.get("motion_strength", 1.0)),
            )
            if abs(transform.scale - 1.0) < 0.001:
                return pixmap, transform
            return pixmap.scaled(
                max(1, round(pixmap.width() * transform.scale)),
                max(1, round(pixmap.height() * transform.scale)),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ), transform

        def _emit_motion_debug(self, kind: str, data: dict, transform) -> None:
            motion = str(data.get("motion", "None"))
            if motion == "None":
                return
            last_time = self._last_motion_debug.get(kind, -999.0)
            if self._current_time - last_time < 0.5:
                return
            self._last_motion_debug[kind] = self._current_time
            self.previewMotionDebug.emit(
                f"[PREVIEW_MOTION] type={motion} layer={kind} time={self._current_time:.2f} "
                f"x={float(data.get('x', 0.5)) + transform.x_offset / max(self._canvas_rect().width(), 1):.3f} "
                f"y={float(data.get('y', 0.5)) + transform.y_offset / max(self._canvas_rect().height(), 1):.3f} "
                f"scale={transform.scale:.3f} opacity={transform.opacity:.3f} rotation_delta={transform.rotation_delta:.2f}"
            )

        def _overlay_visible(self, data: dict) -> bool:
            return bool(data["active"]) and float(data.get("start", 0.0)) <= self._current_time <= float(data.get("end", 0.0))

        def _overlay_rect(self, kind: str) -> QRectF:
            data = self._overlays[kind]
            canvas = self._canvas_rect()
            cx = canvas.left() + float(data["x"]) * canvas.width()
            cy = canvas.top() + float(data["y"]) * canvas.height()
            w = float(data["w"])
            h = float(data["h"])
            return QRectF(cx - w / 2, cy - h / 2, w, h)

        def _canvas_rect(self) -> QRectF:
            pixmap = self.pixmap()
            if pixmap is None or pixmap.isNull():
                return QRectF(0, 0, self.width(), self.height())
            x = (self.width() - pixmap.width()) / 2
            y = (self.height() - pixmap.height()) / 2
            return QRectF(x, y, pixmap.width(), pixmap.height())

        def _safe_rect(self, kind: str) -> QRectF:
            areas = self._safe_area_engine.calculate(self.width(), self.height(), platform=self._safe_area_platform)
            normalized = areas.text_safe_rect if kind == "text" else areas.sticker_safe_rect
            return self._rect_from_normalized(normalized)

        def _rect_from_normalized(self, rect: NormalizedRect) -> QRectF:
            canvas = self._canvas_rect()
            return QRectF(
                canvas.left() + rect.x * canvas.width(),
                canvas.top() + rect.y * canvas.height(),
                rect.width * canvas.width(),
                rect.height * canvas.height(),
            )

        def _clamp_to_safe_area(self, kind: str, x: float, y: float) -> tuple[float, float]:
            rect = self._safe_area_engine.calculate(self.width(), self.height(), platform=self._safe_area_platform)
            safe = rect.sticker_safe_rect if kind == "sticker" else rect.text_safe_rect
            return min(max(x, safe.x), safe.x + safe.width), min(max(y, safe.y), safe.y + safe.height)

        def safe_rect(self) -> tuple[int, int, int, int]:
            rect = self._safe_rect("text")
            return int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
else:
    class PreviewCanvas:  # type: ignore[no-redef]
        pass
