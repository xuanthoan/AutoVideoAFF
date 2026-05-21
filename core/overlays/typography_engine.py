"""Shared Qt/QPainter typography renderer for preview and export parity."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from core.normalized_layout import NormalizedLayoutEngine, REFERENCE_HEIGHT
from core.overlays.template_manager import TextTemplate
from highlight.svg_templates import SVGHighlightItem
from utils.ffmpeg_helper import app_root


try:
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPainterPath, QPen
    from PySide6.QtSvg import QSvgRenderer
except ImportError:  # allows non-GUI CI imports when PySide6 is absent
    QByteArray = QRectF = Qt = QColor = QFont = QFontDatabase = QGuiApplication = QImage = QPainter = QPainterPath = QPen = QSvgRenderer = None


@dataclass(frozen=True, slots=True)
class TypographyStyle:
    line_spacing_ratio: float = 0.32
    horizontal_padding_ratio: float = 0.95
    vertical_padding_ratio: float = 0.58
    border_radius_ratio: float = 0.42
    shadow_opacity: float = 0.22
    max_width_ratio: float = 0.74


class TypographyEngine:
    def __init__(self) -> None:
        self.layout = NormalizedLayoutEngine()

    def scale_factor(self, video_height: int) -> float:
        return video_height / REFERENCE_HEIGHT

    def scale(self, value: float, video_height: int) -> int:
        return self.layout.denormalize_font_size(self.layout.normalize_font_size(value), video_height)


class SocialTypographyRenderer:
    """Render TikTok-style text into transparent RGBA assets using Qt."""

    FONT_FILES = ("Montserrat-ExtraBold.ttf", "Poppins-ExtraBold.ttf")
    FONT_FAMILIES = ("Montserrat ExtraBold", "Montserrat", "Poppins ExtraBold", "Poppins")
    _fonts_loaded = False
    _owned_app = None

    def __init__(self, style: TypographyStyle | None = None) -> None:
        self.style = style or TypographyStyle()
        self.layout = NormalizedLayoutEngine()

    def render_image(self, text: str, template: TextTemplate, font_size: float, canvas_width: int, canvas_height: int):
        """Return a minimal text bounding-box image, never a full-frame canvas."""
        if QImage is None:
            raise RuntimeError("PySide6 is required to render social typography assets.")
        self._ensure_qt_app()
        self._load_fonts()
        font_ratio = self.layout.normalize_font_size(font_size)
        scaled_font = max(12, self.layout.denormalize_font_size(font_ratio, canvas_height))
        font = self._font(scaled_font)
        probe = QImage(8, 8, QImage.Format_ARGB32_Premultiplied)
        probe.fill(Qt.transparent)
        painter = QPainter(probe)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        lines = text.splitlines() or [text]
        max_text_width = max(metrics.horizontalAdvance(line) for line in lines) if lines else 1
        line_spacing = round(scaled_font * self.style.line_spacing_ratio)
        pad_x = round(scaled_font * self.style.horizontal_padding_ratio)
        pad_y = round(scaled_font * self.style.vertical_padding_ratio)
        text_height = len(lines) * metrics.height() + max(0, len(lines) - 1) * line_spacing
        max_box_width = round(canvas_width * self.style.max_width_ratio)
        box_width = min(max_text_width + pad_x * 2, max_box_width)
        box_height = text_height + pad_y * 2
        shadow_pad = max(6, round(scaled_font * 0.18))
        image = QImage(box_width + shadow_pad * 2, box_height + shadow_pad * 2, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter.end()

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        box = QRectF(shadow_pad, shadow_pad, box_width, box_height)
        if template.name == "Orange Quote SVG":
            return self._render_orange_quote_svg(text, scaled_font, canvas_height)
        if template.name == "Blue Tag Vector":
            self._draw_blue_tag_vector(painter, box, lines, font, metrics, pad_x, pad_y, line_spacing)
        elif template.name == "Orange Quote Vector":
            self._draw_orange_quote_vector(painter, box, lines, font, metrics, pad_x, pad_y, line_spacing)
        else:
            radius = scaled_font * self.style.border_radius_ratio
            painter.setBrush(QColor(template.box_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(box, radius, radius)
            painter.setFont(font)
            painter.setPen(QColor(template.font_color))
            y = box.top() + pad_y
            for line in lines:
                line_rect = QRectF(box.left() + pad_x, y, box.width() - pad_x * 2, metrics.height())
                painter.drawText(line_rect, Qt.AlignHCenter | Qt.AlignVCenter, line)
                y += metrics.height() + line_spacing
        painter.end()
        return image

    def _render_orange_quote_svg(self, text: str, scaled_font: int, canvas_height: int):
        template_path = app_root() / "assets" / "vector_highlight_templates" / "orange_quote_template.svg"
        item = SVGHighlightItem(template_path=template_path, text=text, font_size=scaled_font, template_id="orange_quote_template")
        markup = item.svg_markup()
        root = ET.fromstring(markup)
        node = root.find(".//*[@id='dynamic_text']")
        if node is not None:
            node.set("x", "390")
            node.set("text-anchor", "middle")
            node.set("dominant-baseline", "middle")
            node.set("y", "184")
            node.set("font-size", f"{float(scaled_font):.2f}")
            node.text = text or ""
            try:
                for _ in range(10):
                    bbox = self._text_bbox(node.text or "", float(node.get("font-size", scaled_font)))
                    if bbox <= 620:
                        break
                    node.set("font-size", f"{max(24.0, float(node.get('font-size')) * 0.9):.2f}")
            except Exception:
                pass
        updated = ET.tostring(root, encoding="unicode")
        renderer = QSvgRenderer(QByteArray(updated.encode("utf-8")))
        size = renderer.defaultSize()
        scale = max(0.5, canvas_height / 1920)
        width = max(1, int(size.width() * scale))
        height = max(1, int(size.height() * scale))
        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter, QRectF(0, 0, width, height))
        painter.end()
        return image

    def _text_bbox(self, text: str, font_size: float) -> int:
        font = self._font(max(12, int(font_size)))
        probe = QImage(8, 8, QImage.Format_ARGB32_Premultiplied)
        probe.fill(Qt.transparent)
        p = QPainter(probe)
        p.setFont(font)
        w = p.fontMetrics().horizontalAdvance(text)
        p.end()
        return int(w)


    def _draw_blue_tag_vector(self, painter, box: QRectF, lines: list[str], font, metrics, pad_x: int, pad_y: int, line_spacing: int) -> None:
        outer = QPainterPath()
        cut = min(box.width() * 0.11, box.height() * 0.35)
        outer.moveTo(box.left() + cut, box.top())
        outer.lineTo(box.right() - 10, box.top())
        outer.lineTo(box.right(), box.top() + 10)
        outer.lineTo(box.right(), box.bottom())
        outer.lineTo(box.left() + 8, box.bottom())
        outer.lineTo(box.left(), box.bottom() - 8)
        outer.lineTo(box.left(), box.top() + cut)
        outer.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(outer)

        mid = box.adjusted(8, 8, -8, -8)
        painter.setBrush(QColor("#F2542D"))
        painter.drawPath(self._tag_path(mid, cut * 0.75))

        core = mid.adjusted(10, 10, -16, -14)
        painter.setBrush(QColor("#173F7A"))
        painter.drawPath(self._tag_path(core, cut * 0.55))

        accent = core.adjusted(0, core.height() - max(8, core.height() * 0.14), 0, 6)
        painter.setBrush(QColor("#FACC15"))
        painter.drawRect(accent)

        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        y = core.top() + pad_y * 0.6
        for line in lines:
            line_rect = QRectF(core.left() + pad_x * 0.5, y, core.width() - pad_x, metrics.height())
            painter.drawText(line_rect, Qt.AlignHCenter | Qt.AlignVCenter, line)
            y += metrics.height() + line_spacing

    def _tag_path(self, rect: QRectF, cut: float):
        path = QPainterPath()
        path.moveTo(rect.left() + cut, rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left() + 4, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - 4)
        path.lineTo(rect.left(), rect.top() + cut)
        path.closeSubpath()
        return path

    def _draw_orange_quote_vector(self, painter, box: QRectF, lines: list[str], font, metrics, pad_x: int, pad_y: int, line_spacing: int) -> None:
        outer = box.adjusted(2, 2, -2, -2)
        painter.setPen(QPen(QColor("#FFFFFF"), 8))
        painter.setBrush(QColor("#F2542D"))
        painter.drawRoundedRect(outer, 6, 6)

        painter.setPen(QPen(QColor("#1E3A8A"), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(outer.adjusted(8, 8, -8, -8), 4, 4)

        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        y = outer.top() + pad_y + 18
        for line in lines:
            line_rect = QRectF(outer.left() + pad_x, y, outer.width() - pad_x * 2, metrics.height())
            painter.drawText(line_rect, Qt.AlignHCenter | Qt.AlignVCenter, line)
            y += metrics.height() + line_spacing

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        quote_w = max(14, metrics.height() * 0.45)
        painter.drawRoundedRect(QRectF(outer.left() + 18, outer.top() + 12, quote_w, quote_w * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(outer.left() + 18 + quote_w * 0.85, outer.top() + 12, quote_w, quote_w * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(outer.right() - 18 - quote_w * 1.85, outer.bottom() - 12 - quote_w * 1.3, quote_w, quote_w * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(outer.right() - 18 - quote_w, outer.bottom() - 12 - quote_w * 1.3, quote_w, quote_w * 1.3), 2, 2)

        cx, cy = outer.right() - 24, outer.top() + 8
        r = max(16, metrics.height() * 0.9)
        painter.setBrush(QColor("#1E3A8A"))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        painter.setBrush(QColor("#FFFFFF"))
        tri = QPainterPath()
        tri.moveTo(cx - r * 0.25, cy - r * 0.35)
        tri.lineTo(cx - r * 0.25, cy + r * 0.35)
        tri.lineTo(cx + r * 0.40, cy)
        tri.closeSubpath()
        painter.drawPath(tri)

    def render_png(self, path: Path, text: str, template: TextTemplate, font_size: float, canvas_width: int, canvas_height: int) -> Path:
        """Write only the typography region PNG; FFmpeg positions it on the final canvas."""
        image = self.render_image(text, template, font_size, canvas_width, canvas_height)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(path), "PNG"):
            raise RuntimeError(f"Unable to write typography PNG: {path}")
        return path

    @classmethod
    def _ensure_qt_app(cls) -> None:
        if QGuiApplication is None or QGuiApplication.instance() is not None:
            return
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._owned_app = QGuiApplication([sys.argv[0] or "AutoVideoAFF"])

    @classmethod
    def _load_fonts(cls) -> None:
        if cls._fonts_loaded or QFontDatabase is None:
            return
        font_dir = app_root() / "assets" / "fonts"
        for filename in cls.FONT_FILES:
            font_path = font_dir / filename
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
        cls._fonts_loaded = True

    @classmethod
    def _font(cls, size: int):
        available = set(QFontDatabase.families()) if QFontDatabase is not None else set()
        family = next((candidate for candidate in cls.FONT_FAMILIES if candidate in available), cls.FONT_FAMILIES[0])
        font = QFont(family, size)
        font.setWeight(QFont.ExtraBold)
        font.setStyleStrategy(QFont.PreferAntialias)
        return font
