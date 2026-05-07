"""Realtime preview canvas with safe-area and snap guides."""
from __future__ import annotations

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QPainter, QPen
    from PySide6.QtWidgets import QLabel
except ImportError:  # lets non-GUI CI import architecture modules without PySide6 installed
    Qt = Signal = QPainter = QPen = QLabel = None


if QLabel:
    class PreviewCanvas(QLabel):
        overlayMoved = Signal(float, float)

        def __init__(self) -> None:
            super().__init__("Preview")
            self.setMinimumSize(420, 720)
            self.setAlignment(Qt.AlignCenter)
            self.setStyleSheet("background:#111;color:#aaa;border:1px solid #333;")
            self._snap_x: int | None = None
            self._snap_y: int | None = None

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            safe = self.safe_rect()
            painter.setPen(QPen(Qt.green, 1, Qt.DashLine))
            painter.drawRect(safe[0], safe[1], safe[2], safe[3])
            painter.setPen(QPen(Qt.blue, 2))
            if self._snap_x is not None:
                painter.drawLine(self._snap_x, 0, self._snap_x, self.height())
            if self._snap_y is not None:
                painter.drawLine(0, self._snap_y, self.width(), self._snap_y)

        def safe_rect(self) -> tuple[int, int, int, int]:
            left = int(self.width() * 0.05)
            top = int(self.height() * 0.08)
            right = int(self.width() * 0.05)
            bottom = int(self.height() * 0.16)
            return left, top, self.width() - left - right, self.height() - top - bottom
else:
    class PreviewCanvas:  # type: ignore[no-redef]
        pass
