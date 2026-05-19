from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from .base_vector_highlight import BaseVectorHighlight

SAFE_MARGIN = 40.0
SHADOW_OFFSET_X = 16.0
SHADOW_OFFSET_Y = 14.0
OUTER_BORDER = 14.0
ORANGE_INSET = 12.0
NAVY_INSET_X = 18.0
NAVY_INSET_Y = 14.0


class BlueTagVectorHighlight(BaseVectorHighlight):
    def boundingRect(self) -> QRectF:
        return self._outer_rect.adjusted(-SAFE_MARGIN, -SAFE_MARGIN, SAFE_MARGIN + SHADOW_OFFSET_X, SAFE_MARGIN + SHADOW_OFFSET_Y)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect

        # Base tag geometry: left chamfer + right slanted tip
        base = self._tag_polygon(r)

        # 1) yellow shadow layer
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawPath(self._translate_path(base, SHADOW_OFFSET_X, SHADOW_OFFSET_Y))

        # 2) thick white outer border/base
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(base)

        # 3) orange/red layer
        orange_rect = r.adjusted(OUTER_BORDER, OUTER_BORDER * 0.85, -OUTER_BORDER, -OUTER_BORDER * 0.75)
        orange = self._tag_polygon(orange_rect)
        painter.setBrush(QColor("#F2542D"))
        painter.drawPath(orange)

        # 4) dark navy inner panel
        navy_rect = orange_rect.adjusted(NAVY_INSET_X, NAVY_INSET_Y, -NAVY_INSET_X * 0.85, -NAVY_INSET_Y)
        navy = self._tag_polygon(navy_rect)
        painter.setBrush(QColor("#163E7A"))
        painter.drawPath(navy)

        # 5) text
        self._text_rect = navy_rect.adjusted(self._font_size * 0.35, 0, -self._font_size * 0.35, 0)
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        self._deco_rect = r.adjusted(0, 0, SHADOW_OFFSET_X, SHADOW_OFFSET_Y)
        self.draw_debug_boxes(painter)

    def _tag_polygon(self, rect: QRectF) -> QPainterPath:
        left_cut = min(rect.height() * 0.35, rect.width() * 0.17)
        right_slant = min(rect.height() * 0.18, rect.width() * 0.08)
        path = QPainterPath()
        path.moveTo(rect.left() + left_cut, rect.top())
        path.lineTo(rect.right() - right_slant, rect.top())
        path.lineTo(rect.right(), rect.top() + right_slant)
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left() + 8, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - 8)
        path.lineTo(rect.left(), rect.top() + left_cut)
        path.closeSubpath()
        return path

    @staticmethod
    def _translate_path(path: QPainterPath, dx: float, dy: float) -> QPainterPath:
        moved = QPainterPath(path)
        moved.translate(dx, dy)
        return moved
