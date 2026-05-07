"""Right-side workflow controls."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
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
    QCheckBox = QComboBox = QDoubleSpinBox = QFileDialog = QFormLayout = QGroupBox = QPushButton = QSpinBox = QTextEdit = QVBoxLayout = QWidget = None

from core.overlays.template_manager import TemplateManager, TextTemplate


if QWidget:
    class WorkflowPanel(QWidget):
        changed = Signal()
        imagePoolSelected = Signal(list)
        stickerSelected = Signal(str)
        stickerControlsChanged = Signal(float, float, str)
        textChanged = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self.template_manager = TemplateManager()
            self.scene_shuffle = QCheckBox("Scene Shuffle")
            self.scene_shuffle.setChecked(True)
            self.scene_sensitivity = QSpinBox(); self.scene_sensitivity.setRange(10, 80); self.scene_sensitivity.setValue(30)
            self.image_composite = QCheckBox("Image Composite")
            self.text_overlay = QCheckBox("Text Overlay")
            self.sticker_overlay = QCheckBox("Sticker Overlay")
            self.text = QTextEdit()
            self.text.setPlaceholderText("TEXT - nhập text để tự tạo layer")
            self.template = QComboBox()
            self._populate_template_combo()
            self.font_size = QSpinBox(); self.font_size.setRange(16, 260); self.font_size.setValue(96)
            self.motion = QComboBox(); self.motion.addItems(["None", "Fade", "Slide", "Zoom", "Bounce", "Elastic"])
            self.sticker_scale = QDoubleSpinBox(); self.sticker_scale.setRange(0.1, 5.0); self.sticker_scale.setSingleStep(0.1); self.sticker_scale.setValue(1.0); self.sticker_scale.setSuffix("x")
            self.sticker_rotation = QSpinBox(); self.sticker_rotation.setRange(-360, 360); self.sticker_rotation.setValue(0); self.sticker_rotation.setSuffix("°")
            self.sticker_motion = QComboBox(); self.sticker_motion.addItems(["None", "Fade In", "Fade Out", "Bounce", "Pop", "Slide Up", "Slide Down"])
            image_button = QPushButton("Chọn image pool")
            sticker_button = QPushButton("Chọn sticker")
            image_button.clicked.connect(self.pick_images)
            sticker_button.clicked.connect(self.pick_sticker)
            self.text.textChanged.connect(lambda: self.textChanged.emit(self.text.toPlainText()))
            self.sticker_scale.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_rotation.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_motion.currentTextChanged.connect(lambda _text: self.emit_sticker_controls())
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

            return QSize(48, 20)

        def _template_icon(self, template: TextTemplate):
            pixmap = QPixmap(48, 20)
            pixmap.fill(QColor("transparent"))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            colors = [QColor(color) for color in template.preview_colors]
            width = 24
            for index, color in enumerate(colors):
                painter.fillRect(index * width, 0, width, 20, color)
            painter.setPen(QPen(QColor("#222222"), 1))
            painter.drawRoundedRect(0, 0, 47, 19, 4, 4)
            painter.end()
            return QIcon(pixmap)

        def _scene_group(self):
            group = QGroupBox("PANEL 1 — SCENE SHUFFLE")
            form = QFormLayout(group); form.addRow(self.scene_shuffle); form.addRow("Scene Sensitivity", self.scene_sensitivity)
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
            form = QFormLayout(group)
            form.addRow(self.sticker_overlay); form.addRow(button)
            form.addRow("Scale", self.sticker_scale)
            form.addRow("Rotation", self.sticker_rotation)
            form.addRow("Motion", self.sticker_motion)
            return group

        def emit_sticker_controls(self) -> None:
            self.stickerControlsChanged.emit(
                float(self.sticker_scale.value()),
                float(self.sticker_rotation.value()),
                self.sticker_motion.currentText(),
            )

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
