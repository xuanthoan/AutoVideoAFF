from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from .base_vector_highlight import BaseVectorHighlight

OUTER_PADDING = 12.0
CHAMFER_RATIO = 0.24
SHADOW_OFFSET_X = 10.0
SHADOW_OFFSET_Y = 9.0
ORANGE_INSET = 10.0
NAVY_INSET_X = 14.0
NAVY_INSET_Y = 12.0
ACCENT_HEIGHT_RATIO = 0.16


class BlueTagVectorHighlight(BaseVectorHighlight):
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = self._outer_rect
        chamfer = min(r.height() * CHAMFER_RATIO, r.width() * 0.17)

        # 1) yellow shadow layer
        yellow = self._tag_path(r.translated(SHADOW_OFFSET_X, SHADOW_OFFSET_Y), chamfer)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FACC15"))
        painter.drawPath(yellow)

        # 2) white outer border/base shape
        white = self._tag_path(r, chamfer)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(white)

        # 3) orange/red layer
        orange_rect = r.adjusted(OUTER_PADDING, OUTER_PADDING * 0.9, -OUTER_PADDING, -OUTER_PADDING * 0.7)
        orange = self._tag_path(orange_rect, chamfer * 0.78)
        painter.setBrush(QColor("#F2542D"))
        painter.drawPath(orange)

        # 4) dark navy center panel
        navy_rect = orange_rect.adjusted(NAVY_INSET_X, NAVY_INSET_Y, -NAVY_INSET_X * 0.85, -NAVY_INSET_Y)
        navy = self._tag_path(navy_rect, chamfer * 0.58)
        painter.setBrush(QColor("#173F7A"))
        painter.drawPath(navy)

        # 5) text
        text_rect = navy_rect.adjusted(self._font_size * 0.35, 0, -self._font_size * 0.35, 0)
        self._text_rect = text_rect
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(text_rect, Qt.AlignCenter, self._text)

        accent_h = max(6.0, navy_rect.height() * ACCENT_HEIGHT_RATIO)
        self._deco_rect = r.united(QPainterPath(navy).boundingRect().adjusted(0, navy_rect.height() - accent_h, 0, accent_h))
        self.draw_debug_boxes(painter)

    def _tag_path(self, rect, cut):
        path = QPainterPath()
        path.moveTo(rect.left() + cut, rect.top())
        path.lineTo(rect.right() - 6, rect.top())
        path.lineTo(rect.right(), rect.top() + 6)
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left() + 6, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - 6)
        path.lineTo(rect.left(), rect.top() + cut)
        path.closeSubpath()
        return path
