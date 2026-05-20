from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from .base_vector_highlight import BaseVectorHighlight

SAFE_MARGIN = 56.0
OUTER_BORDER = 22.0
FRAME_STROKE = 9.0
PLAY_SIZE_RATIO = 0.78
PLAY_OVERLAP_X = 36.0
PLAY_OVERLAP_Y = 24.0
QUOTE_BLOCK_W = 0.17
QUOTE_BLOCK_H = 0.28


class OrangeQuoteVectorHighlight(BaseVectorHighlight):
    def __init__(self, text: str = "SALE", font_size: int = 54) -> None:
        super().__init__(text, font_size)
        self.play_rotation_angle = 0.0

    def boundingRect(self) -> QRectF:
        return self._outer_rect.adjusted(-SAFE_MARGIN, -SAFE_MARGIN * 1.25, SAFE_MARGIN * 1.7, SAFE_MARGIN * 1.45)

    def step_animation(self, degrees: float = 1.2) -> None:
        self.play_rotation_angle = (self.play_rotation_angle + degrees) % 360.0
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect

        # 1) thick white border/base
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(r, 12, 12)

        # 2) orange body
        orange = r.adjusted(OUTER_BORDER, OUTER_BORDER, -OUTER_BORDER, -OUTER_BORDER)
        painter.setBrush(QColor("#F2542D"))
        painter.drawRoundedRect(orange, 9, 9)

        # 3) decorative partial navy frame
        painter.setPen(QPen(QColor("#173F7A"), FRAME_STROKE, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
        painter.setBrush(Qt.NoBrush)
        left_x = orange.left() + 24
        right_x = orange.right() - 24
        top_y = orange.top() + 28
        bottom_y = orange.bottom() - 18
        painter.drawLine(left_x, top_y, left_x, bottom_y)
        painter.drawLine(left_x, top_y, right_x, top_y)
        painter.drawLine(left_x + 8, bottom_y, right_x - 10, bottom_y)
        painter.drawLine(right_x, top_y, right_x, top_y + 28)

        # 4/5) custom rounded quote marks via paths
        qh = orange.height() * QUOTE_BLOCK_H
        qw = orange.width() * QUOTE_BLOCK_W * 0.34
        top_quote = self._double_quote_path(orange.left() + 34, orange.top() - qh * 0.54, qw, qh, flip=False)
        bottom_quote = self._double_quote_path(orange.right() - 34 - qw * 2.1, orange.bottom() - qh * 0.10, qw, qh, flip=True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawPath(top_quote)
        painter.drawPath(bottom_quote)

        # 6) centered text
        self._text_rect = orange.adjusted(self._font_size * 1.12, self._font_size * 0.48, -self._font_size * 1.28, -self._font_size * 0.44)
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        # 7) larger overlapping play button
        radius = max(38.0, orange.height() * PLAY_SIZE_RATIO * 0.5)
        cx = right_x - PLAY_OVERLAP_X
        cy = top_y - PLAY_OVERLAP_Y
        circle_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QColor("#173F7A"))
        painter.drawEllipse(circle_rect)

        # 8) rounded triangle + optional S
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.play_rotation_angle)
        painter.setBrush(QColor("#FFFFFF"))
        tri = QPainterPath()
        tri.moveTo(-radius * 0.28, -radius * 0.34)
        tri.quadTo(-radius * 0.22, 0, -radius * 0.28, radius * 0.34)
        tri.lineTo(radius * 0.42, 0)
        tri.closeSubpath()
        painter.drawPath(tri)
        painter.restore()

        s_font = QFont(self._font)
        s_font.setPointSizeF(max(12.0, radius * 0.38))
        painter.setFont(s_font)
        painter.setPen(QColor("#173F7A"))
        painter.drawText(QRectF(cx - radius * 0.20, cy - radius * 0.07, radius * 0.38, radius * 0.28), Qt.AlignCenter, "S")

        self._deco_rect = orange.united(circle_rect).adjusted(-qh * 0.9, -qh * 1.2, qh * 1.0, qh * 0.9)
        self.draw_debug_boxes(painter)

    def _double_quote_path(self, x: float, y: float, w: float, h: float, flip: bool = False) -> QPainterPath:
        p = QPainterPath()
        gap = w * 0.35
        for i in range(2):
            dx = i * (w + gap)
            if not flip:
                p.moveTo(x + dx + w * 0.1, y + h * 0.95)
                p.quadTo(x + dx + w * 0.05, y + h * 0.55, x + dx + w * 0.1, y + h * 0.18)
                p.lineTo(x + dx + w * 0.78, y + h * 0.18)
                p.quadTo(x + dx + w * 0.62, y + h * 0.52, x + dx + w * 0.66, y + h * 0.95)
            else:
                p.moveTo(x + dx + w * 0.22, y + h * 0.10)
                p.quadTo(x + dx + w * 0.38, y + h * 0.48, x + dx + w * 0.34, y + h * 0.90)
                p.lineTo(x + dx + w * 0.90, y + h * 0.90)
                p.quadTo(x + dx + w * 0.95, y + h * 0.55, x + dx + w * 0.90, y + h * 0.10)
            p.closeSubpath()
        return p
