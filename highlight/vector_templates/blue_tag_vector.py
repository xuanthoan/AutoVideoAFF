from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from .base_vector_highlight import BaseVectorHighlight


class BlueTagVectorHighlight(BaseVectorHighlight):
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect
        cut = min(r.height() * 0.33, r.width() * 0.16)

        outer = QPainterPath()
        outer.moveTo(r.left() + cut, r.top())
        outer.lineTo(r.right() - 14, r.top())
        outer.lineTo(r.right(), r.top() + 14)
        outer.lineTo(r.right(), r.bottom())
        outer.lineTo(r.left() + 10, r.bottom())
        outer.lineTo(r.left(), r.bottom() - 10)
        outer.lineTo(r.left(), r.top() + cut)
        outer.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(outer)

        orange = r.adjusted(10, 10, -10, -10)
        painter.setBrush(QColor("#F2542D"))
        painter.drawPath(self._tag_path(orange, cut * 0.72))

        blue = orange.adjusted(10, 9, -18, -12)
        painter.setBrush(QColor("#163E7A"))
        painter.drawPath(self._tag_path(blue, cut * 0.52))

        accent = blue.adjusted(0, blue.height() * 0.82, 0, 8)
        painter.setBrush(QColor("#FACC15"))
        painter.drawRect(accent)

        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(self._text_rect, Qt.AlignCenter, self._text)

        self._deco_rect = r
        self.draw_debug_boxes(painter)

    def _tag_path(self, rect, cut):
        path = QPainterPath()
        path.moveTo(rect.left() + cut, rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left() + 4, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - 4)
        path.lineTo(rect.left(), rect.top() + cut)
        path.closeSubpath()
        return path
