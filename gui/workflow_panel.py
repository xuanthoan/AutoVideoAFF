"""Right-side workflow controls."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Signal
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QListWidget,
        QPushButton,
        QRadioButton,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    Signal = QColor = QIcon = QPainter = QPen = QPixmap = None
    QButtonGroup = QCheckBox = QComboBox = QDoubleSpinBox = QFileDialog = QFormLayout = None
    QGroupBox = QListWidget = QPushButton = QRadioButton = QSpinBox = QTextEdit = QVBoxLayout = QWidget = None

from core.overlays.template_manager import TemplateManager, TextTemplate
from models.project_state import WorkflowMode


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
            self.pipeline_group = QButtonGroup(self)
            self.pipeline_buttons: dict[WorkflowMode, QRadioButton] = {}
            for mode in WorkflowMode:
                button = QRadioButton(mode.value)
                self.pipeline_buttons[mode] = button
                self.pipeline_group.addButton(button)
            self.pipeline_buttons[WorkflowMode.PIPELINE_1].setChecked(True)

            self.scene_sensitivity = QSpinBox(); self.scene_sensitivity.setRange(10, 80); self.scene_sensitivity.setValue(30)
            self.fallback_min = QDoubleSpinBox(); self.fallback_min.setRange(1.0, 10.0); self.fallback_min.setValue(3.0); self.fallback_min.setSuffix("s")
            self.fallback_max = QDoubleSpinBox(); self.fallback_max.setRange(1.0, 12.0); self.fallback_max.setValue(5.0); self.fallback_max.setSuffix("s")
            self.keep_first_segment = QCheckBox("Keep first segment"); self.keep_first_segment.setChecked(True)
            self.shuffle_random = QCheckBox("Random shuffle"); self.shuffle_random.setChecked(True)

            self.image_list = QListWidget()
            self.image_height = QSpinBox(); self.image_height.setRange(20, 60); self.image_height.setValue(35); self.image_height.setSuffix("%")
            self.overlap = QSpinBox(); self.overlap.setRange(0, 20); self.overlap.setValue(5); self.overlap.setSuffix("%")
            self.crop_focus = QComboBox(); self.crop_focus.addItems(["top", "center", "bottom"]); self.crop_focus.setCurrentText("center")
            self.fade_curve = QComboBox(); self.fade_curve.addItems(["linear", "smooth", "strong"])

            self.text = QTextEdit()
            self.text.setPlaceholderText("TEXT - nhập text để tự tạo layer")
            self.template = QComboBox()
            self._populate_template_combo()
            self.font_size = QSpinBox(); self.font_size.setRange(18, 260); self.font_size.setValue(96)
            self.motion = QComboBox(); self.motion.addItems(["None", "Fade", "Slide", "Bounce", "Pop", "Scale", "Drift"])

            self.sticker_scale = QDoubleSpinBox(); self.sticker_scale.setRange(0.1, 5.0); self.sticker_scale.setSingleStep(0.1); self.sticker_scale.setValue(1.0); self.sticker_scale.setSuffix("x")
            self.sticker_rotation = QSpinBox(); self.sticker_rotation.setRange(-360, 360); self.sticker_rotation.setValue(0); self.sticker_rotation.setSuffix("°")
            self.sticker_motion = QComboBox(); self.sticker_motion.addItems(["None", "Fade In", "Fade Out", "Bounce", "Pop", "Slide Up", "Slide Down"])
            sticker_button = QPushButton("Chọn sticker")
            image_button = QPushButton("Chọn ảnh (multi-select)")
            image_button.clicked.connect(self.pick_images)
            sticker_button.clicked.connect(self.pick_sticker)

            self.text.textChanged.connect(lambda: self.textChanged.emit(self.text.toPlainText()))
            self.sticker_scale.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_rotation.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_motion.currentTextChanged.connect(lambda _text: self.emit_sticker_controls())
            self.image_height.valueChanged.connect(lambda _value: self._clamp_overlap())

            layout = QVBoxLayout(self)
            for group in (
                self._pipeline_group(),
                self._scene_group(),
                self._image_group(image_button),
                self._text_group(),
                self._sticker_group(sticker_button),
            ):
                layout.addWidget(group)
            layout.addStretch()

        def selected_workflow_mode(self) -> WorkflowMode:
            for mode, button in self.pipeline_buttons.items():
                if button.isChecked():
                    return mode
            return WorkflowMode.PIPELINE_1

        def set_image_pool(self, paths: list[Path]) -> None:
            self.image_list.clear()
            for path in paths:
                self.image_list.addItem(path.name)

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
            width = 24
            for index, color in enumerate(template.preview_colors):
                painter.fillRect(index * width, 0, width, 20, QColor(color))
            painter.setPen(QPen(QColor("#222222"), 1))
            painter.drawRoundedRect(0, 0, 47, 19, 4, 4)
            painter.end()
            return QIcon(pixmap)

        def _pipeline_group(self):
            group = QGroupBox("1. PIPELINE PANEL")
            form = QFormLayout(group)
            for mode in WorkflowMode:
                form.addRow(self.pipeline_buttons[mode])
            return group

        def _scene_group(self):
            group = QGroupBox("2. SHUFFLE PANEL")
            form = QFormLayout(group)
            form.addRow("Scene Sensitivity", self.scene_sensitivity)
            form.addRow("Fallback min", self.fallback_min)
            form.addRow("Fallback max", self.fallback_max)
            form.addRow(self.shuffle_random)
            form.addRow(self.keep_first_segment)
            return group

        def _image_group(self, button):
            group = QGroupBox("3. IMAGE COMPOSITOR PANEL")
            form = QFormLayout(group)
            form.addRow(button)
            form.addRow("Images", self.image_list)
            form.addRow("Crop focus", self.crop_focus)
            form.addRow("Image height", self.image_height)
            form.addRow("Overlap", self.overlap)
            form.addRow("Fade curve", self.fade_curve)
            return group

        def _text_group(self):
            group = QGroupBox("4. TEXT PANEL")
            form = QFormLayout(group)
            form.addRow("TEXT", self.text)
            form.addRow("Template", self.template)
            form.addRow("Font size", self.font_size)
            form.addRow("Motion", self.motion)
            return group

        def _sticker_group(self, button):
            group = QGroupBox("5. STICKER PANEL")
            form = QFormLayout(group)
            form.addRow(button)
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
            paths = [Path(file) for file in files]
            self.set_image_pool(paths)
            self.imagePoolSelected.emit(paths)

        def pick_sticker(self) -> None:
            file, _ = QFileDialog.getOpenFileName(self, "Sticker", "", "Images (*.png *.webp *.jpg)")
            if file:
                self.stickerSelected.emit(file)

        def _clamp_overlap(self) -> None:
            self.overlap.setMaximum(min(20, self.image_height.value()))
else:
    class WorkflowPanel:  # type: ignore[no-redef]
        pass
