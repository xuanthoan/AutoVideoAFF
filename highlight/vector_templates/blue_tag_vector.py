from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from .base_vector_highlight import BaseVectorHighlight

SAFE_MARGIN = 48.0
SHADOW_OFFSET_X = 10.0
SHADOW_OFFSET_Y = 8.0
WHITE_BORDER = 20.0
ORANGE_INSET = 16.0
NAVY_INSET_X = 14.0
NAVY_INSET_Y = 14.0
RIGHT_SOFT_SLANT = 0.11
LEFT_CUT_RATIO = 0.30


class BlueTagVectorHighlight(BaseVectorHighlight):
    def boundingRect(self) -> QRectF:
        return self._outer_rect.adjusted(-SAFE_MARGIN, -SAFE_MARGIN, SAFE_MARGIN + SHADOW_OFFSET_X + 12, SAFE_MARGIN + SHADOW_OFFSET_Y + 10)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect

        base = self._tag_polygon(r)

        # 1. subtle yellow shadow only bottom/right
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawPath(self._translate_path(base, SHADOW_OFFSET_X, SHADOW_OFFSET_Y))

        # 2. thick white outer border
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(base)

        # 3. thick orange layer
        orange_rect = r.adjusted(WHITE_BORDER, WHITE_BORDER * 0.85, -WHITE_BORDER * 0.95, -WHITE_BORDER * 0.72)
        orange = self._tag_polygon(orange_rect)
        painter.setBrush(QColor("#F2542D"))
        painter.drawPath(orange)

        # 4. navy inner panel
        navy_rect = orange_rect.adjusted(NAVY_INSET_X, NAVY_INSET_Y, -NAVY_INSET_X * 0.86, -NAVY_INSET_Y * 0.92)
        navy = self._tag_polygon(navy_rect)
        painter.setBrush(QColor("#163E7A"))
        painter.drawPath(navy)

        # 5. text
        self._text_rect = navy_rect.adjusted(self._font_size * 0.52, 0, -self._font_size * 0.52, 0)
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        self._deco_rect = r.adjusted(0, 0, SHADOW_OFFSET_X + 8, SHADOW_OFFSET_Y + 8)
        self.draw_debug_boxes(painter)

    def _tag_polygon(self, rect: QRectF) -> QPainterPath:
        left_cut = min(rect.height() * LEFT_CUT_RATIO, rect.width() * 0.16)
        right_slant = min(rect.height() * RIGHT_SOFT_SLANT, rect.width() * 0.06)
        path = QPainterPath()
        path.moveTo(rect.left() + left_cut, rect.top())
        path.lineTo(rect.right() - right_slant, rect.top())
        path.lineTo(rect.right(), rect.top() + right_slant)
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left() + 10, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - 10)
        path.lineTo(rect.left(), rect.top() + left_cut)
        path.closeSubpath()
        return path

    @staticmethod
    def _translate_path(path: QPainterPath, dx: float, dy: float) -> QPainterPath:
        moved = QPainterPath(path)
        moved.translate(dx, dy)
        return moved
