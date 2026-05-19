from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from .base_vector_highlight import BaseVectorHighlight

SAFE_MARGIN = 40.0
OUTER_BORDER = 16.0
FRAME_INSET = 20.0
FRAME_STROKE = 8.0
QUOTE_FONT_SCALE = 1.08
PLAY_BUTTON_RATIO = 0.72
PLAY_OVERLAP_X = 18.0
PLAY_OVERLAP_Y = 16.0


class OrangeQuoteVectorHighlight(BaseVectorHighlight):
    def __init__(self, text: str = "SALE", font_size: int = 54) -> None:
        super().__init__(text, font_size)
        self.play_rotation_angle = 0.0

    def boundingRect(self) -> QRectF:
        return self._outer_rect.adjusted(-SAFE_MARGIN, -SAFE_MARGIN * 1.2, SAFE_MARGIN * 1.35, SAFE_MARGIN * 1.25)

    def step_animation(self, degrees: float = 1.2) -> None:
        self.play_rotation_angle = (self.play_rotation_angle + degrees) % 360.0
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect

        # 1) thick white outer border/base
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(r, 10, 10)

        # 2) orange main body
        orange = r.adjusted(OUTER_BORDER, OUTER_BORDER, -OUTER_BORDER, -OUTER_BORDER)
        painter.setBrush(QColor("#F2542D"))
        painter.drawRoundedRect(orange, 8, 8)

        # 3) navy outline frame
        frame = orange.adjusted(FRAME_INSET, FRAME_INSET, -FRAME_INSET, -FRAME_INSET)
        painter.setPen(QPen(QColor("#173F7A"), FRAME_STROKE))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(frame)

        # 4+5) quote glyph marks (actual quote shapes)
        quote_font = QFont(self._font)
        quote_font.setPointSizeF(max(24.0, self._font_size * QUOTE_FONT_SCALE))
        quote_font.setBold(True)
        painter.setFont(quote_font)
        painter.setPen(QColor("#FACC15"))
        painter.drawText(QRectF(frame.left() + 8, frame.top() - self._font_size * 0.85, self._font_size * 2.4, self._font_size * 1.7), Qt.AlignLeft | Qt.AlignVCenter, "““")
        painter.drawText(QRectF(frame.right() - self._font_size * 2.6, frame.bottom() - self._font_size * 0.35, self._font_size * 2.5, self._font_size * 1.7), Qt.AlignRight | Qt.AlignVCenter, "””")

        # 6) centered white bold text
        self._text_rect = orange.adjusted(self._font_size * 1.0, self._font_size * 0.34, -self._font_size * 1.0, -self._font_size * 0.34)
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        # 7) navy circular play button overlapping top-right
        radius = max(26.0, orange.height() * PLAY_BUTTON_RATIO * 0.5)
        cx = frame.right() - PLAY_OVERLAP_X
        cy = frame.top() - PLAY_OVERLAP_Y
        circle_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#173F7A"))
        painter.drawEllipse(circle_rect)

        # 8) white rounded triangle play icon (center-rotation fixed)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.play_rotation_angle)
        painter.setBrush(QColor("#FFFFFF"))
        tri = QPainterPath()
        tri.moveTo(-radius * 0.30, -radius * 0.34)
        tri.quadTo(-radius * 0.28, 0, -radius * 0.30, radius * 0.34)
        tri.lineTo(radius * 0.40, 0)
        tri.closeSubpath()
        painter.drawPath(tri)
        painter.restore()

        self._deco_rect = orange.united(circle_rect).adjusted(-self._font_size * 0.6, -self._font_size, self._font_size * 0.9, self._font_size * 0.8)
        self.draw_debug_boxes(painter)
