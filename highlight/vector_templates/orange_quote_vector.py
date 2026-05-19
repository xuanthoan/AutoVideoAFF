from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from .base_vector_highlight import BaseVectorHighlight


class OrangeQuoteVectorHighlight(BaseVectorHighlight):
    def __init__(self, text: str = "SALE", font_size: int = 54) -> None:
        super().__init__(text, font_size)
        self.play_rotation_angle = 0.0

    def step_animation(self, degrees: float = 1.2) -> None:
        self.play_rotation_angle = (self.play_rotation_angle + degrees) % 360.0
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect

        painter.setPen(QPen(QColor("#FFFFFF"), 8))
        painter.setBrush(QColor("#F2542D"))
        painter.drawRoundedRect(r.adjusted(3, 3, -3, -3), 8, 8)

        inner = r.adjusted(13, 13, -13, -13)
        painter.setPen(QPen(QColor("#173F7A"), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(inner, 4, 4)

        q = max(14.0, self._font_size * 0.45)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawRoundedRect(QRectF(inner.left() + 18, inner.top() - 8, q, q * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(inner.left() + 18 + q * 0.9, inner.top() - 8, q, q * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(inner.right() - 18 - q * 1.9, inner.bottom() + 8 - q * 1.3, q, q * 1.3), 2, 2)
        painter.drawRoundedRect(QRectF(inner.right() - 18 - q, inner.bottom() + 8 - q * 1.3, q, q * 1.3), 2, 2)

        cx = inner.right() - 10
        cy = inner.top() - 8
        radius = max(24.0, self._font_size * 0.75)
        circle_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setBrush(QColor("#173F7A"))
        painter.drawEllipse(circle_rect)

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.play_rotation_angle)
        painter.setBrush(QColor("#FFFFFF"))
        tri = QPainterPath()
        tri.moveTo(-radius * 0.28, -radius * 0.38)
        tri.lineTo(-radius * 0.28, radius * 0.38)
        tri.lineTo(radius * 0.45, 0)
        tri.closeSubpath()
        painter.drawPath(tri)
        painter.restore()

        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        self._deco_rect = QRectF(inner.left(), inner.top() - radius, inner.width(), inner.height() + radius)
        self.draw_debug_boxes(painter)
