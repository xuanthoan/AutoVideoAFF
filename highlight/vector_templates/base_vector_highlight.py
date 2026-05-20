from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem


class BaseVectorHighlight(QGraphicsItem):
    def __init__(self, text: str = "SALE", font_size: int = 54) -> None:
        super().__init__()
        self._text = text
        self._font_size = font_size
        self._debug = False
        self._outer_rect = QRectF(0, 0, 400, 140)
        self._text_rect = QRectF()
        self._deco_rect = QRectF()
        self._font = QFont("Montserrat", self._font_size)
        self._font.setBold(True)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.update_geometry()

    def boundingRect(self) -> QRectF:
        pad = 8.0
        return self._outer_rect.adjusted(-pad, -pad, pad, pad)

    def set_text(self, text: str) -> None:
        self._text = text or " "
        self.update_geometry()

    def set_font_size(self, size: int) -> None:
        self._font_size = max(16, int(size))
        self._font = QFont("Montserrat", self._font_size)
        self._font.setBold(True)
        self.update_geometry()

    def set_debug_boxes(self, enabled: bool) -> None:
        self._debug = enabled
        self.update()

    def text(self) -> str:
        return self._text

    def font_size(self) -> int:
        return self._font_size

    def update_geometry(self) -> None:
        self.prepareGeometryChange()
        metrics = QFontMetricsF(self._font)
        text_width = metrics.horizontalAdvance(self._text)
        text_height = metrics.height()
        width = max(260.0, text_width + self.padding_left() + self.padding_right() + self.decoration_width())
        height = max(120.0, text_height + self.padding_top() + self.padding_bottom())
        self._outer_rect = QRectF(0, 0, width, height)
        self._text_rect = QRectF(
            self.padding_left(),
            (height - text_height) / 2.0,
            max(20.0, width - self.padding_left() - self.padding_right()),
            text_height,
        )
        self._deco_rect = QRectF(0, 0, width, height)
        self.update()

    def export_png(self, path: str) -> None:
        rect = self.boundingRect()
        image = QImage(int(rect.width()) + 4, int(rect.height()) + 4, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(-rect.left() + 2, -rect.top() + 2)
        self.paint(painter, None, None)
        painter.end()
        image.save(path, "PNG")

    def draw_debug_boxes(self, painter: QPainter) -> None:
        if not self._debug:
            return
        painter.save()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#00B8FF"), 1, Qt.DashLine))
        painter.drawRect(self._outer_rect)
        painter.setPen(QPen(QColor("#FF006E"), 1, Qt.DashDotLine))
        painter.drawRect(self._text_rect)
        painter.setPen(QPen(QColor("#8338EC"), 1, Qt.DotLine))
        painter.drawRect(self._deco_rect)
        painter.restore()

    def padding_left(self) -> float:
        return self._font_size * 1.2

    def padding_right(self) -> float:
        return self._font_size * 1.2

    def padding_top(self) -> float:
        return self._font_size * 0.55

    def padding_bottom(self) -> float:
        return self._font_size * 0.55

    def decoration_width(self) -> float:
        return self._font_size * 0.45
