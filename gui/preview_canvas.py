"""Realtime preview canvas with safe-area, drag, and snap guides."""
from __future__ import annotations

from pathlib import Path

from core.safe_area_engine import NormalizedRect, SafeAreaEngine

try:
    from PySide6.QtCore import QRectF, Qt, Signal
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QLabel
except ImportError:  # lets non-GUI CI import architecture modules without PySide6 installed
    QRectF = Qt = Signal = QColor = QPainter = QPen = QPixmap = QLabel = None


if QLabel:
    class PreviewCanvas(QLabel):
        overlayMoved = Signal(str, float, float)
        SNAP_THRESHOLD = 10

        def __init__(self) -> None:
            super().__init__("Preview")
            self.setMinimumSize(520, 780)
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
            self._overlays = {
                "text": {"active": False, "x": 0.5, "y": 0.35, "w": 220, "h": 70},
                "sticker": {"active": False, "x": 0.5, "y": 0.55, "w": 120, "h": 120},
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
            for kind in ("sticker", "text"):
                if self._overlay_rect(kind).contains(event.position()):
                    self._drag_kind = kind
                    return
            return super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if not self._drag_kind:
                return super().mouseMoveEvent(event)
            x = event.position().x()
            y = event.position().y()
            center_x = self.width() / 2
            center_y = self.height() / 2
            self._snap_x = None
            self._snap_y = None
            if self._snap_enabled and abs(x - center_x) <= self.SNAP_THRESHOLD:
                x = center_x
                self._snap_x = int(center_x)
            if self._snap_enabled and abs(y - center_y) <= self.SNAP_THRESHOLD:
                y = center_y
                self._snap_y = int(center_y)
            norm_x = min(max(x / max(self.width(), 1), 0.0), 1.0)
            norm_y = min(max(y / max(self.height(), 1), 0.0), 1.0)
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
            self._draw_overlay_proxy(painter, "text", QColor(245, 124, 77, 180))
            self._draw_overlay_proxy(painter, "sticker", QColor(255, 255, 255, 150))
            guide_pen = QPen(QColor(90, 190, 255, 170), 2)
            painter.setPen(guide_pen)
            if self._snap_x is not None:
                painter.drawLine(self._snap_x, 0, self._snap_x, self.height())
            if self._snap_y is not None:
                painter.drawLine(0, self._snap_y, self.width(), self._snap_y)

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

        def _draw_overlay_proxy(self, painter: QPainter, kind: str, color: QColor) -> None:
            if not self._overlays[kind]["active"]:
                return
            rect = self._overlay_rect(kind)
            painter.setPen(QPen(color, 2))
            painter.drawRoundedRect(rect, 8, 8)
            painter.drawText(rect, Qt.AlignCenter, "TEXT" if kind == "text" else "STICKER")

        def _overlay_rect(self, kind: str) -> QRectF:
            data = self._overlays[kind]
            cx = float(data["x"]) * self.width()
            cy = float(data["y"]) * self.height()
            w = float(data["w"])
            h = float(data["h"])
            return QRectF(cx - w / 2, cy - h / 2, w, h)

        def _safe_rect(self, kind: str) -> QRectF:
            areas = self._safe_area_engine.calculate(self.width(), self.height(), platform=self._safe_area_platform)
            normalized = areas.text_safe_rect if kind == "text" else areas.sticker_safe_rect
            return self._rect_from_normalized(normalized)

        def _rect_from_normalized(self, rect: NormalizedRect) -> QRectF:
            return QRectF(rect.x * self.width(), rect.y * self.height(), rect.width * self.width(), rect.height * self.height())

        def _clamp_to_safe_area(self, kind: str, x: float, y: float) -> tuple[float, float]:
            rect = self._safe_area_engine.calculate(self.width(), self.height(), platform=self._safe_area_platform)
            safe = rect.text_safe_rect if kind == "text" else rect.sticker_safe_rect
            return min(max(x, safe.x), safe.x + safe.width), min(max(y, safe.y), safe.y + safe.height)

        def safe_rect(self) -> tuple[int, int, int, int]:
            rect = self._safe_rect("text")
            return int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
else:
    class PreviewCanvas:  # type: ignore[no-redef]
        pass
