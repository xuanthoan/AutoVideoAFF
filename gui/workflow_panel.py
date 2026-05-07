"""Right-side workflow controls."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QPushButton,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    Qt = Signal = QColor = QIcon = QPainter = QPen = QPixmap = None
    QCheckBox = QComboBox = QFileDialog = QFormLayout = QGroupBox = QPushButton = QSpinBox = QTextEdit = QVBoxLayout = QWidget = None

from core.overlays.template_manager import TemplateManager, TextTemplate


if QWidget:
    class WorkflowPanel(QWidget):
        changed = Signal()
        imagePoolSelected = Signal(list)
        stickerSelected = Signal(str)
        textChanged = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self.template_manager = TemplateManager()
            self.scene_shuffle = QCheckBox("Scene Shuffle")
            self.scene_shuffle.setChecked(True)
            self.image_composite = QCheckBox("Image Composite")
            self.text_overlay = QCheckBox("Text Overlay")
            self.sticker_overlay = QCheckBox("Sticker Overlay")
            self.text = QTextEdit()
            self.text.setPlaceholderText("TEXT - nhập text để tự tạo layer")
            self.template = QComboBox()
            self._populate_template_combo()
            self.font_size = QSpinBox(); self.font_size.setRange(16, 260); self.font_size.setValue(96)
            self.motion = QComboBox(); self.motion.addItems(["None", "Fade", "Slide", "Zoom", "Bounce", "Elastic"])
            image_button = QPushButton("Chọn image pool")
            sticker_button = QPushButton("Chọn sticker")
            image_button.clicked.connect(self.pick_images)
            sticker_button.clicked.connect(self.pick_sticker)
            self.text.textChanged.connect(lambda: self.textChanged.emit(self.text.toPlainText()))
            layout = QVBoxLayout(self)
            for group in (self._scene_group(), self._image_group(image_button), self._text_group(), self._sticker_group(sticker_button)):
                layout.addWidget(group)
            layout.addStretch()

        def _populate_template_combo(self) -> None:
            self.template.setIconSize(self._template_icon_size())
            for template in self.template_manager.BUILT_INS:
                self.template.addItem(self._template_icon(template), template.name)

        def _template_icon_size(self):
            from PySide6.QtCore import QSize

            return QSize(72, 22)

        def _template_icon(self, template: TextTemplate):
            pixmap = QPixmap(72, 22)
            pixmap.fill(QColor("transparent"))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            colors = [QColor(color) for color in template.preview_colors]
            width = 72 // len(colors)
            for index, color in enumerate(colors):
                painter.fillRect(index * width, 0, width, 22, color)
            painter.setPen(QPen(QColor("#222222"), 1))
            painter.drawRoundedRect(0, 0, 71, 21, 4, 4)
            painter.end()
            return QIcon(pixmap)

        def _scene_group(self):
            group = QGroupBox("PANEL 1 — SCENE SHUFFLE")
            form = QFormLayout(group); form.addRow(self.scene_shuffle)
            return group

        def _image_group(self, button):
            group = QGroupBox("PANEL 2 — IMAGE COMPOSITE")
            form = QFormLayout(group); form.addRow(self.image_composite); form.addRow(button)
            return group

        def _text_group(self):
            group = QGroupBox("PANEL 3 — TEXT OVERLAY")
            form = QFormLayout(group)
            form.addRow(self.text_overlay); form.addRow("TEXT", self.text); form.addRow("Template", self.template); form.addRow("Font size", self.font_size); form.addRow("Motion", self.motion)
            return group

        def _sticker_group(self, button):
            group = QGroupBox("PANEL 4 — STICKER OVERLAY")
            form = QFormLayout(group); form.addRow(self.sticker_overlay); form.addRow(button)
            return group

        def pick_images(self) -> None:
            files, _ = QFileDialog.getOpenFileNames(self, "Image pool", "", "Images (*.png *.jpg *.jpeg *.webp)")
            self.imagePoolSelected.emit([Path(file) for file in files])

        def pick_sticker(self) -> None:
            file, _ = QFileDialog.getOpenFileName(self, "Sticker", "", "Images (*.png *.webp *.jpg)")
            if file:
                self.stickerSelected.emit(file)
else:
    class WorkflowPanel:  # type: ignore[no-redef]
        pass
