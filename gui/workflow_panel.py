"""Right-side compact workflow controls with pipeline-dependent UI locking."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QGraphicsOpacityEffect,
        QGroupBox,
        QListWidget,
        QPushButton,
        QRadioButton,
        QSlider,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    Qt = Signal = QColor = QIcon = QPainter = QPen = QPixmap = None
    QButtonGroup = QCheckBox = QComboBox = QDoubleSpinBox = QFileDialog = QFormLayout = QGraphicsOpacityEffect = None
    QGroupBox = QListWidget = QPushButton = QRadioButton = QSlider = QSpinBox = QTextEdit = QVBoxLayout = QWidget = None

from core.overlays.highlight_library import HIGHLIGHT_ANIMATIONS, HIGHLIGHT_STYLE_NAMES
from core.overlays.template_manager import TemplateManager, TextTemplate
from models.project_state import WorkflowMode
from models.watermark_overlay import WATERMARK_COLORS, WATERMARK_FONTS, WATERMARK_DENSITY_COUNTS


PIPELINE_CONFIG = {
    WorkflowMode.PIPELINE_1: {"shuffle": True, "image": True, "watermark": True, "text": False, "highlight": False, "sticker": False},
    WorkflowMode.PIPELINE_2: {"shuffle": True, "image": True, "watermark": True, "text": True, "highlight": True, "sticker": True},
    WorkflowMode.PIPELINE_3: {"shuffle": True, "image": False, "watermark": True, "text": True, "highlight": True, "sticker": True},
    WorkflowMode.PIPELINE_4: {"shuffle": False, "image": False, "watermark": True, "text": True, "highlight": True, "sticker": True},
}


if QWidget:
    class WorkflowPanel(QWidget):
        changed = Signal()
        imagePoolSelected = Signal(list)
        stickerSelected = Signal(str)
        stickerControlsChanged = Signal(float, float, str)
        textChanged = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self._ui_ready = False
            self.template_manager = TemplateManager()
            self.pipeline_group = QButtonGroup(self)
            self.pipeline_buttons: dict[WorkflowMode, QRadioButton] = {}
            for mode in WorkflowMode:
                button = QRadioButton(mode.value)
                self.pipeline_buttons[mode] = button
                self.pipeline_group.addButton(button)
            default_button = self.pipeline_buttons[WorkflowMode.PIPELINE_1]
            default_button.blockSignals(True)
            default_button.setChecked(True)
            default_button.blockSignals(False)

            self.scene_sensitivity = QSpinBox(); self.scene_sensitivity.setRange(10, 80); self.scene_sensitivity.setValue(30)
            self.fallback_min = QDoubleSpinBox(); self.fallback_min.setRange(1.0, 10.0); self.fallback_min.setValue(3.0); self.fallback_min.setSuffix("s")
            self.fallback_max = QDoubleSpinBox(); self.fallback_max.setRange(1.0, 12.0); self.fallback_max.setValue(5.0); self.fallback_max.setSuffix("s")

            self.image_list = QListWidget(); self.image_list.setMaximumHeight(58)
            self.image_height = QSpinBox(); self.image_height.setRange(20, 60); self.image_height.setValue(35); self.image_height.setSuffix("%")
            self.overlap = QSpinBox(); self.overlap.setRange(0, 20); self.overlap.setValue(5); self.overlap.setSuffix("%")
            self.crop_focus = QComboBox(); self.crop_focus.addItems(["top", "center", "bottom"]); self.crop_focus.setCurrentText("center")
            self.fade_curve = QComboBox(); self.fade_curve.addItems(["linear", "smooth", "strong"])

            self.watermark_enabled = QCheckBox("Enable Watermark")
            self.watermark_text = QTextEdit(); self.watermark_text.setMaximumHeight(48); self.watermark_text.setPlaceholderText("@shopabc, TikTok: @abc, MY BRAND...")
            self.watermark_font = QComboBox(); self.watermark_font.addItems(WATERMARK_FONTS)
            self.watermark_font_size = QSpinBox(); self.watermark_font_size.setRange(12, 120); self.watermark_font_size.setValue(44)
            self.watermark_color = QComboBox(); self.watermark_color.addItems(WATERMARK_COLORS)
            self.watermark_opacity = QSpinBox(); self.watermark_opacity.setRange(3, 60); self.watermark_opacity.setValue(15); self.watermark_opacity.setSuffix("%")
            self.watermark_rotation = QSpinBox(); self.watermark_rotation.setRange(-45, 45); self.watermark_rotation.setValue(-15); self.watermark_rotation.setSuffix("°")
            self.watermark_random_position = QCheckBox("Enable Random Position"); self.watermark_random_position.setChecked(True)
            self.watermark_slow_motion = QCheckBox("Enable Slow Floating Motion"); self.watermark_slow_motion.setChecked(True)
            self.watermark_density = QComboBox(); self.watermark_density.addItems(WATERMARK_DENSITY_COUNTS.keys())

            self.text = QTextEdit(); self.text.setMaximumHeight(70)
            self.text.setPlaceholderText("TEXT - nhập text để tự tạo layer")
            self.template = QComboBox()
            self._populate_template_combo()
            self.font_size = QSpinBox(); self.font_size.setRange(18, 260); self.font_size.setValue(96)
            self.motion = QComboBox(); self.motion.addItems(["None", "Fade In", "Fade Out", "Pop", "Bounce", "Scale", "Scale Up", "Scale Down", "Float", "Slide Left", "Slide Right", "Slide Up", "Slide Down", "Pulse", "Shake"])
            self.text_motion_speed = self._motion_speed_slider()
            self.text_motion_strength = self._motion_strength_slider()

            self.highlight_enabled = QCheckBox("Enable Highlight")
            self.highlight_text = QTextEdit(); self.highlight_text.setMaximumHeight(54); self.highlight_text.setPlaceholderText("SALE 50%, BEST SELLER, MUA NGAY...")
            self.highlight_style = QComboBox(); self.highlight_style.addItems(HIGHLIGHT_STYLE_NAMES)
            self.highlight_animation = QComboBox(); self.highlight_animation.addItems(HIGHLIGHT_ANIMATIONS)
            self.highlight_animation.setCurrentText("Pop")

            self.sticker_scale = QDoubleSpinBox(); self.sticker_scale.setRange(0.05, 0.45); self.sticker_scale.setSingleStep(0.01); self.sticker_scale.setDecimals(2); self.sticker_scale.setValue(0.16); self.sticker_scale.setSuffix(" canvas")
            self.sticker_rotation = QSpinBox(); self.sticker_rotation.setRange(-360, 360); self.sticker_rotation.setValue(0); self.sticker_rotation.setSuffix("°")
            self.sticker_motion = QComboBox(); self.sticker_motion.addItems(["None", "Fade In", "Fade Out", "Pop", "Bounce", "Scale", "Scale Up", "Scale Down", "Float", "Slide Left", "Slide Right", "Slide Up", "Slide Down", "Pulse", "Shake", "Rotate Float"])
            self.sticker_motion_speed = self._motion_speed_slider()
            self.sticker_motion_strength = self._motion_strength_slider()
            self.link_motion_speed = QCheckBox("Link Text & Sticker Speed")
            self.link_motion_speed.setChecked(False)
            self.link_motion_speed.setToolTip("When enabled, sticker motion speed follows text motion speed.")

            sticker_button = QPushButton("Chọn sticker")
            image_button = QPushButton("Chọn ảnh (multi-select)")

            layout = QVBoxLayout(self)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)
            self.pipeline_panel = self._pipeline_group()
            self.shuffle_panel = self._scene_group()
            self.image_panel = self._image_group(image_button)
            self.watermark_panel = self._watermark_group()
            self.text_panel = self._text_group()
            self.highlight_panel = self._highlight_group()
            self.sticker_panel = self._sticker_group(sticker_button)
            for group in (self.pipeline_panel, self.shuffle_panel, self.image_panel, self.watermark_panel, self.text_panel, self.highlight_panel, self.sticker_panel):
                layout.addWidget(group)
            layout.addStretch()
            self._ui_ready = True
            self._connect_signals(image_button, sticker_button)
            self.apply_pipeline_ui_state()

        def _connect_signals(self, image_button: QPushButton, sticker_button: QPushButton) -> None:
            for button in self.pipeline_buttons.values():
                button.toggled.connect(lambda _checked: self.apply_pipeline_ui_state())
            image_button.clicked.connect(self.pick_images)
            sticker_button.clicked.connect(self.pick_sticker)
            self.text.textChanged.connect(lambda: self.textChanged.emit(self.text.toPlainText()))
            self.sticker_scale.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_rotation.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_motion.currentTextChanged.connect(lambda _text: self.emit_sticker_controls())
            self.text_motion_speed.valueChanged.connect(lambda _value: self._sync_linked_motion_speed())
            self.sticker_motion_speed.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_motion_strength.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.link_motion_speed.toggled.connect(lambda _checked: self._set_speed_link_state())
            self.image_height.valueChanged.connect(lambda _value: self._clamp_overlap())

        def selected_workflow_mode(self) -> WorkflowMode:
            for mode, button in self.pipeline_buttons.items():
                if button.isChecked():
                    return mode
            return WorkflowMode.PIPELINE_1

        def apply_pipeline_ui_state(self) -> None:
            if not getattr(self, "_ui_ready", False):
                return
            required_panels = ("shuffle_panel", "image_panel", "watermark_panel", "text_panel", "highlight_panel", "sticker_panel")
            if any(not hasattr(self, panel_name) for panel_name in required_panels):
                return
            config = PIPELINE_CONFIG[self.selected_workflow_mode()]
            self._set_panel_state(self.shuffle_panel, config["shuffle"])
            self._set_panel_state(self.image_panel, config["image"])
            self._set_panel_state(self.watermark_panel, config["watermark"])
            self._set_panel_state(self.text_panel, config["text"])
            self._set_panel_state(self.highlight_panel, config["highlight"])
            self._set_panel_state(self.sticker_panel, config["sticker"])
            self.changed.emit()

        def _set_panel_state(self, panel: QGroupBox, enabled: bool) -> None:
            panel.setEnabled(enabled)
            effect = panel.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(panel)
                panel.setGraphicsEffect(effect)
            effect.setOpacity(1.0 if enabled else 0.38)
            panel.setToolTip("" if enabled else "Disabled in current pipeline")
            title_color = "#e8e8e8" if enabled else "#777"
            panel.setStyleSheet(f"QGroupBox {{ color: {title_color}; font-weight: 600; margin-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 6px; }}")

        def set_image_pool(self, paths: list[Path]) -> None:
            self.image_list.clear()
            for path in paths:
                self.image_list.addItem(path.name)

        def _populate_template_combo(self) -> None:
            self.template.setIconSize(self._template_icon_size())
            self.template.addItem(TemplateManager.RANDOM_TEMPLATE_NAME)
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

        def _compact_form(self, group: QGroupBox) -> QFormLayout:
            form = QFormLayout(group)
            form.setContentsMargins(8, 8, 8, 8)
            form.setVerticalSpacing(4)
            form.setHorizontalSpacing(8)
            return form

        MOTION_SPEED_VALUES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)

        def _motion_speed_slider(self) -> QSlider:
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, len(self.MOTION_SPEED_VALUES) - 1)
            slider.setValue(self.MOTION_SPEED_VALUES.index(1.0))
            slider.setSingleStep(1)
            slider.setPageStep(1)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(1)
            slider.setToolTip("Motion Speed: 0.25x, 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x, 3.0x")
            return slider

        def _motion_strength_slider(self) -> QSlider:
            slider = QSlider(Qt.Horizontal)
            slider.setRange(50, 200)
            slider.setValue(100)
            slider.setToolTip("Motion Strength: 100 = normal; 50 = subtle; 200 = strong")
            return slider

        def motion_speed_ratio(self, slider: QSlider) -> float:
            index = min(max(int(slider.value()), 0), len(self.MOTION_SPEED_VALUES) - 1)
            return self.MOTION_SPEED_VALUES[index]

        def text_motion_speed_ratio(self) -> float:
            return self.motion_speed_ratio(self.text_motion_speed)

        def sticker_motion_speed_ratio(self) -> float:
            return self.motion_speed_ratio(self.sticker_motion_speed)

        @staticmethod
        def motion_strength_ratio(slider: QSlider) -> float:
            return max(0.05, float(slider.value()) / 100.0)

        def slider_ratio(self, slider: QSlider) -> float:
            # Backward-compatible helper for older callers; speed sliders use the discrete mapping.
            if int(slider.maximum()) == len(self.MOTION_SPEED_VALUES) - 1:
                return self.motion_speed_ratio(slider)
            return self.motion_strength_ratio(slider)

        def _pipeline_group(self):
            group = QGroupBox("1. PIPELINE")
            form = self._compact_form(group)
            for mode in WorkflowMode:
                form.addRow(self.pipeline_buttons[mode])
            return group

        def _scene_group(self):
            group = QGroupBox("2. SHUFFLE")
            form = self._compact_form(group)
            form.addRow("Sensitivity", self.scene_sensitivity)
            form.addRow("Fallback min", self.fallback_min)
            form.addRow("Fallback max", self.fallback_max)
            return group

        def _image_group(self, button):
            group = QGroupBox("3. IMAGE")
            form = self._compact_form(group)
            form.addRow(button)
            form.addRow("Images", self.image_list)
            form.addRow("Crop", self.crop_focus)
            form.addRow("Height", self.image_height)
            form.addRow("Overlap", self.overlap)
            form.addRow("Fade", self.fade_curve)
            return group

        def _watermark_group(self):
            group = QGroupBox("4. WATERMARK")
            form = self._compact_form(group)
            form.addRow(self.watermark_enabled)
            form.addRow("Watermark Text", self.watermark_text)
            form.addRow("Font", self.watermark_font)
            form.addRow("Font Size", self.watermark_font_size)
            form.addRow("Font Color", self.watermark_color)
            form.addRow("Opacity", self.watermark_opacity)
            form.addRow("Rotation", self.watermark_rotation)
            form.addRow(self.watermark_random_position)
            form.addRow(self.watermark_slow_motion)
            form.addRow("Density", self.watermark_density)
            return group

        def _text_group(self):
            group = QGroupBox("5. TEXT")
            form = self._compact_form(group)
            form.addRow("TEXT", self.text)
            form.addRow("Template", self.template)
            form.addRow("Font", self.font_size)
            form.addRow("Motion", self.motion)
            form.addRow("Motion Speed", self.text_motion_speed)
            form.addRow("Strength", self.text_motion_strength)
            return group


        def _highlight_group(self):
            group = QGroupBox("6. HIGHLIGHT")
            form = self._compact_form(group)
            form.addRow(self.highlight_enabled)
            form.addRow("Highlight Text", self.highlight_text)
            form.addRow("Style", self.highlight_style)
            form.addRow("Animation", self.highlight_animation)
            return group

        def _sticker_group(self, button):
            group = QGroupBox("7. STICKER")
            form = self._compact_form(group)
            form.addRow(button)
            form.addRow("Scale", self.sticker_scale)
            form.addRow("Rotation", self.sticker_rotation)
            form.addRow("Motion", self.sticker_motion)
            form.addRow("Motion Speed", self.sticker_motion_speed)
            form.addRow("Strength", self.sticker_motion_strength)
            form.addRow(self.link_motion_speed)
            return group

        def _sync_linked_motion_speed(self) -> None:
            if not self.link_motion_speed.isChecked():
                return
            if self.sticker_motion_speed.value() != self.text_motion_speed.value():
                self.sticker_motion_speed.setValue(self.text_motion_speed.value())
            else:
                self.emit_sticker_controls()

        def _set_speed_link_state(self) -> None:
            linked = self.link_motion_speed.isChecked()
            self.sticker_motion_speed.setEnabled(not linked)
            self._sync_linked_motion_speed()

        def emit_sticker_controls(self) -> None:
            self.stickerControlsChanged.emit(float(self.sticker_scale.value()), float(self.sticker_rotation.value()), self.sticker_motion.currentText())

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
