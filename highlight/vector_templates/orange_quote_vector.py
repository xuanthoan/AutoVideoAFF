from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from .base_vector_highlight import BaseVectorHighlight

OUTER_BORDER = 12.0
FRAME_INSET = 18.0
FRAME_STROKE = 7.0
QUOTE_SIZE_RATIO = 0.45
PLAY_BUTTON_RATIO = 0.82
PLAY_OVERLAP_X = 16.0
PLAY_OVERLAP_Y = 14.0


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

        # 1) white outer border/base
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(r, 9, 9)

        # 2) orange background
        orange = r.adjusted(OUTER_BORDER, OUTER_BORDER, -OUTER_BORDER, -OUTER_BORDER)
        painter.setBrush(QColor("#F2542D"))
        painter.drawRoundedRect(orange, 7, 7)

        # 3) navy outline frame
        frame = orange.adjusted(FRAME_INSET, FRAME_INSET, -FRAME_INSET, -FRAME_INSET)
        painter.setPen(QPen(QColor("#173F7A"), FRAME_STROKE))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(frame)

        # 4) yellow quote marks
        q = max(16.0, self._font_size * QUOTE_SIZE_RATIO)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawRoundedRect(QRectF(frame.left() + 10, frame.top() - q * 0.75, q, q * 1.45), 2, 2)
        painter.drawRoundedRect(QRectF(frame.left() + 10 + q * 0.95, frame.top() - q * 0.75, q, q * 1.45), 2, 2)
        painter.drawRoundedRect(QRectF(frame.right() - 10 - q * 1.95, frame.bottom() - q * 0.7, q, q * 1.45), 2, 2)
        painter.drawRoundedRect(QRectF(frame.right() - 10 - q, frame.bottom() - q * 0.7, q, q * 1.45), 2, 2)

        # 5) centered text
        text_rect = orange.adjusted(self._font_size * 0.95, self._font_size * 0.28, -self._font_size * 0.95, -self._font_size * 0.28)
        self._text_rect = text_rect
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(text_rect, Qt.AlignCenter, self._text)

        # 6) play button circle (overlapping top-right)
        radius = max(24.0, self._font_size * PLAY_BUTTON_RATIO)
        cx = frame.right() - PLAY_OVERLAP_X
        cy = frame.top() - PLAY_OVERLAP_Y
        circle_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QColor("#173F7A"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(circle_rect)

        # 7) white play triangle (rotating around exact center)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.play_rotation_angle)
        painter.setBrush(QColor("#FFFFFF"))
        tri = QPainterPath()
        tri.moveTo(-radius * 0.26, -radius * 0.38)
        tri.lineTo(-radius * 0.26, radius * 0.38)
        tri.lineTo(radius * 0.48, 0)
        tri.closeSubpath()
        painter.drawPath(tri)
        painter.restore()

        self._deco_rect = orange.united(circle_rect)
        self.draw_debug_boxes(painter)
