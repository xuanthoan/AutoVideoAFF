"""Right-side professional workflow controls for mass-production editing."""
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
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QListWidget,
        QPushButton,
        QRadioButton,
        QSpinBox,
        QSizePolicy,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    Qt = Signal = QColor = QIcon = QPainter = QPen = QPixmap = None
    QButtonGroup = QCheckBox = QComboBox = QDoubleSpinBox = QFileDialog = QFormLayout = QGraphicsOpacityEffect = None
    QGridLayout = QGroupBox = QHBoxLayout = QListWidget = QPushButton = QRadioButton = QSpinBox = QSizePolicy = QTextEdit = QVBoxLayout = QWidget = None

from core.overlays.highlight_library import HIGHLIGHT_ANIMATIONS, HIGHLIGHT_STYLE_NAMES
from core.overlays.template_manager import TemplateManager, TextTemplate
from models.project_state import WorkflowMode
from models.watermark_overlay import WATERMARK_COLORS, WATERMARK_DENSITY_COUNTS, WATERMARK_FONTS


PIPELINE_CONFIG = {
    WorkflowMode.PIPELINE_1: {"shuffle": True, "image": True, "watermark": True, "text": False, "highlight": True, "sticker": False},
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

        MOTION_SPEED_VALUES = ("0.25x", "0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x", "3x")

        def __init__(self) -> None:
            super().__init__()
            self._ui_ready = False
            self.template_manager = TemplateManager()
            self.pipeline_group = QButtonGroup(self)
            self.pipeline_buttons: dict[WorkflowMode, QRadioButton] = {}
            for mode in WorkflowMode:
                button = QRadioButton(mode.value)
                button.setMinimumHeight(24)
                self.pipeline_buttons[mode] = button
                self.pipeline_group.addButton(button)
            default_button = self.pipeline_buttons[WorkflowMode.PIPELINE_1]
            default_button.blockSignals(True)
            default_button.setChecked(True)
            default_button.blockSignals(False)

            self.scene_sensitivity = QSpinBox(); self.scene_sensitivity.setRange(10, 80); self.scene_sensitivity.setValue(30)
            self.fallback_min = QDoubleSpinBox(); self.fallback_min.setRange(1.0, 10.0); self.fallback_min.setValue(3.0); self.fallback_min.setSuffix("s")
            self.fallback_max = QDoubleSpinBox(); self.fallback_max.setRange(1.0, 12.0); self.fallback_max.setValue(5.0); self.fallback_max.setSuffix("s")

            self.image_list = QListWidget(); self.image_list.setMaximumHeight(46)
            self.image_height = QSpinBox(); self.image_height.setRange(20, 60); self.image_height.setValue(35); self.image_height.setSuffix("%")
            self.overlap = QSpinBox(); self.overlap.setRange(0, 20); self.overlap.setValue(10); self.overlap.setSuffix("%")
            self.crop_focus = QComboBox(); self.crop_focus.addItems(["top", "center", "bottom"]); self.crop_focus.setCurrentText("center")
            self.fade_curve = QComboBox(); self.fade_curve.addItems(["linear", "smooth", "strong"]); self.fade_curve.setCurrentText("smooth")

            self.watermark_text = QTextEdit(); self.watermark_text.setMaximumHeight(42); self.watermark_text.setPlaceholderText("@shopabc, TikTok: @abc, MY BRAND...")
            self.watermark_font = QComboBox(); self.watermark_font.addItems(WATERMARK_FONTS)
            self.watermark_font_size = QSpinBox(); self.watermark_font_size.setRange(12, 120); self.watermark_font_size.setValue(44)
            self.watermark_color = QComboBox(); self.watermark_color.addItems(WATERMARK_COLORS)
            self.watermark_opacity = QSpinBox(); self.watermark_opacity.setRange(3, 60); self.watermark_opacity.setValue(15); self.watermark_opacity.setSuffix("%")
            self.watermark_density = QComboBox(); self.watermark_density.addItems(WATERMARK_DENSITY_COUNTS.keys()); self.watermark_density.setCurrentText("multi-light")

            self.text = QTextEdit(); self.text.setMaximumHeight(58); self.text.setPlaceholderText("Text overlay")
            self.template = QComboBox(); self._populate_template_combo()
            self.font_size = QSpinBox(); self.font_size.setRange(18, 260); self.font_size.setValue(96)
            self.motion = QComboBox(); self.motion.addItems(["None", "Fade In", "Fade Out", "Pop", "Bounce", "Scale", "Scale Up", "Scale Down", "Float", "Slide Left", "Slide Right", "Slide Up", "Slide Down", "Pulse", "Shake"])
            self.text_motion_speed = self._motion_speed_combo()
            self.text_motion_strength = self._motion_strength_spinbox()

            self.highlight_list = QListWidget(); self.highlight_list.setMaximumHeight(64)
            self.add_highlight_button = QPushButton("Add Highlight")
            self.remove_highlight_button = QPushButton("Remove Selected Highlight")
            self.duplicate_highlight_button = QPushButton("Duplicate Highlight")
            self.highlight_text = QTextEdit(); self.highlight_text.setMaximumHeight(42); self.highlight_text.setPlaceholderText("SALE 50%, BEST SELLER, MUA NGAY...")
            self.highlight_font_size = QSpinBox(); self.highlight_font_size.setRange(20, 160); self.highlight_font_size.setValue(64)
            self.highlight_style = QComboBox(); self.highlight_style.addItems(HIGHLIGHT_STYLE_NAMES)
            self.highlight_animation = QComboBox(); self.highlight_animation.addItems(HIGHLIGHT_ANIMATIONS); self.highlight_animation.setCurrentText("Pop")

            self.sticker_scale = QDoubleSpinBox(); self.sticker_scale.setRange(0.05, 0.45); self.sticker_scale.setSingleStep(0.01); self.sticker_scale.setDecimals(2); self.sticker_scale.setValue(0.16); self.sticker_scale.setSuffix(" canvas")
            self.sticker_rotation = QSpinBox(); self.sticker_rotation.setRange(-360, 360); self.sticker_rotation.setValue(0); self.sticker_rotation.setSuffix("°")
            self.sticker_motion = QComboBox(); self.sticker_motion.addItems(["None", "Fade In", "Fade Out", "Pop", "Bounce", "Scale", "Scale Up", "Scale Down", "Float", "Slide Left", "Slide Right", "Slide Up", "Slide Down", "Pulse", "Shake", "Rotate Float"])
            self.sticker_motion_speed = self._motion_speed_combo()
            self.sticker_motion_strength = self._motion_strength_spinbox()

            self.export_panel = self._styled_group("Export", "panel-export")
            self.export_layout = QHBoxLayout(self.export_panel)
            self.export_layout.setContentsMargins(8, 10, 8, 8)
            self.export_layout.setSpacing(8)

            sticker_button = QPushButton("Choose Sticker")
            image_button = QPushButton("Choose Images")
            self.text_input = self.text
            self.highlight_input = self.highlight_text
            self._apply_compact_widget_style()
            self._apply_responsive_control_widths()

            root = QGridLayout(self)
            root.setContentsMargins(4, 4, 4, 4)
            root.setHorizontalSpacing(8)
            root.setVerticalSpacing(8)
            left_column = QVBoxLayout(); left_column.setSpacing(8); left_column.setContentsMargins(0, 0, 0, 0)
            right_column = QVBoxLayout(); right_column.setSpacing(8); right_column.setContentsMargins(0, 0, 0, 0)

            self.pipeline_panel = self._pipeline_group()
            self.shuffle_panel = self._scene_group()
            self.image_panel = self._image_group(image_button)
            self.watermark_panel = self._watermark_group()
            self.text_panel = self._text_group()
            self.highlight_panel = self._highlight_group()
            self.sticker_panel = self._sticker_group(sticker_button)

            for group in (self.pipeline_panel, self.shuffle_panel, self.image_panel, self.watermark_panel):
                left_column.addWidget(group)
            left_column.addStretch(1)
            for group in (self.text_panel, self.highlight_panel, self.sticker_panel):
                right_column.addWidget(group)
            right_column.addStretch(1)
            root.addLayout(left_column, 0, 0)
            root.addLayout(right_column, 0, 1)
            root.addWidget(self.export_panel, 1, 0, 1, 2)
            root.setColumnStretch(0, 1)
            root.setColumnStretch(1, 1)
            root.setRowStretch(0, 1)
            root.setRowStretch(1, 0)

            self._ui_ready = True
            self._connect_signals(image_button, sticker_button)
            self.apply_pipeline_ui_state()

        def set_export_controls(self, render_button: QPushButton, stop_button: QPushButton, open_output_button: QPushButton) -> None:
            for button in (render_button, stop_button, open_output_button):
                button.setMinimumHeight(32)
                button.setMaximumHeight(36)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.export_layout.addWidget(button, 1)

        def _connect_signals(self, image_button: QPushButton, sticker_button: QPushButton) -> None:
            for button in self.pipeline_buttons.values():
                button.toggled.connect(lambda _checked: self.apply_pipeline_ui_state())
            image_button.clicked.connect(self.pick_images)
            sticker_button.clicked.connect(self.pick_sticker)
            self.text.textChanged.connect(lambda: self.textChanged.emit(self.text.toPlainText()))
            self.sticker_scale.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_rotation.valueChanged.connect(lambda _value: self.emit_sticker_controls())
            self.sticker_motion.currentTextChanged.connect(lambda _text: self.emit_sticker_controls())
            self.sticker_motion_speed.currentTextChanged.connect(lambda _text: self.emit_sticker_controls())
            self.sticker_motion_strength.valueChanged.connect(lambda _value: self.emit_sticker_controls())
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
            return QSize(48, 18)

        def _template_icon(self, template: TextTemplate):
            pixmap = QPixmap(48, 18)
            pixmap.fill(QColor(template.box_color))
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(template.font_color), 2))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "Aa")
            painter.end()
            return QIcon(pixmap)

        def _compact_form(self, group: QGroupBox) -> QFormLayout:
            form = QFormLayout(group)
            form.setContentsMargins(6, 8, 6, 6)
            form.setSpacing(5)
            form.setHorizontalSpacing(6)
            form.setVerticalSpacing(4)
            form.setLabelAlignment(Qt.AlignLeft)
            form.setFormAlignment(Qt.AlignTop)
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            return form

        def _motion_speed_combo(self) -> QComboBox:
            combo = QComboBox()
            combo.addItems(self.MOTION_SPEED_VALUES)
            combo.setCurrentText("1x")
            combo.setToolTip("Motion Speed")
            return combo

        def _motion_strength_spinbox(self) -> QDoubleSpinBox:
            spin = QDoubleSpinBox()
            spin.setRange(0.05, 2.0)
            spin.setSingleStep(0.05)
            spin.setDecimals(2)
            spin.setValue(1.0)
            spin.setSuffix("x")
            spin.setToolTip("Motion Strength")
            return spin

        def motion_speed_ratio(self, control) -> float:
            text = control.currentText() if hasattr(control, "currentText") else str(control.value())
            return max(0.05, float(text.replace("x", "")))

        def text_motion_speed_ratio(self) -> float:
            return self.motion_speed_ratio(self.text_motion_speed)

        def sticker_motion_speed_ratio(self) -> float:
            return self.motion_speed_ratio(self.sticker_motion_speed)

        @staticmethod
        def motion_strength_ratio(control) -> float:
            return max(0.05, float(control.value()))

        def slider_ratio(self, control) -> float:
            return self.motion_speed_ratio(control) if hasattr(control, "currentText") else self.motion_strength_ratio(control)

        def _styled_group(self, title: str, object_name: str) -> QGroupBox:
            group = QGroupBox(title.upper())
            group.setObjectName(object_name)
            return group

        def _pipeline_group(self):
            group = self._styled_group("Pipeline", "panel-pipeline")
            form = self._compact_form(group)
            for mode in WorkflowMode:
                form.addRow(self.pipeline_buttons[mode])
            return group

        def _scene_group(self):
            group = self._styled_group("Shuffle", "panel-shuffle")
            form = self._compact_form(group)
            form.addRow("Sensitivity", self.scene_sensitivity)
            form.addRow("Fallback Minimum", self.fallback_min)
            form.addRow("Fallback Maximum", self.fallback_max)
            return group

        def _image_group(self, button):
            group = self._styled_group("Image", "panel-image")
            form = self._compact_form(group)
            form.addRow(button)
            form.addRow("Crop Focus", self.crop_focus)
            form.addRow("Image Height", self.image_height)
            form.addRow("Overlap", self.overlap)
            form.addRow("Fade Curve", self.fade_curve)
            form.addRow("Images", self.image_list)
            return group

        def _watermark_group(self):
            group = self._styled_group("Watermark", "panel-watermark")
            form = self._compact_form(group)
            form.addRow("Watermark Text", self.watermark_text)
            form.addRow("Font", self.watermark_font)
            form.addRow("Font Size", self.watermark_font_size)
            form.addRow("Font Color", self.watermark_color)
            form.addRow("Opacity", self.watermark_opacity)
            form.addRow("Density", self.watermark_density)
            return group

        def _text_group(self):
            group = self._styled_group("Text", "panel-text")
            form = self._compact_form(group)
            form.addRow("Text", self.text)
            form.addRow("Template", self.template)
            form.addRow("Font Size", self.font_size)
            form.addRow("Animation", self.motion)
            form.addRow("Motion Speed", self.text_motion_speed)
            form.addRow("Motion Strength", self.text_motion_strength)
            return group

        def _highlight_group(self):
            group = self._styled_group("Highlight", "panel-highlight")
            form = self._compact_form(group)
            form.addRow("Highlights", self.highlight_list)
            form.addRow(self.add_highlight_button)
            form.addRow(self.duplicate_highlight_button)
            form.addRow(self.remove_highlight_button)
            form.addRow("Highlight Text", self.highlight_text)
            form.addRow("Highlight Font Size", self.highlight_font_size)
            form.addRow("Style", self.highlight_style)
            form.addRow("Animation", self.highlight_animation)
            return group

        def _sticker_group(self, button):
            group = self._styled_group("Sticker", "panel-sticker")
            form = self._compact_form(group)
            form.addRow(button)
            form.addRow("Scale", self.sticker_scale)
            form.addRow("Rotation", self.sticker_rotation)
            form.addRow("Animation", self.sticker_motion)
            form.addRow("Motion Speed", self.sticker_motion_speed)
            form.addRow("Motion Strength", self.sticker_motion_strength)
            return group

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

        def _apply_responsive_control_widths(self) -> None:
            for widget in (
                self.image_list, self.watermark_text, self.watermark_font, self.watermark_color, self.watermark_density,
                self.text, self.template, self.motion, self.highlight_list, self.highlight_text, self.highlight_style, self.highlight_animation,
                self.add_highlight_button, self.remove_highlight_button, self.duplicate_highlight_button, self.sticker_motion, self.export_panel,
            ):
                widget.setMinimumWidth(0)
                widget.setMaximumWidth(16777215)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            for widget in (self.text, self.highlight_text, self.watermark_text):
                widget.setLineWrapMode(QTextEdit.WidgetWidth)

        def _apply_compact_widget_style(self) -> None:
            self.setStyleSheet(
                """
                QWidget { font-size: 11px; }
                QGroupBox { color: #f0f0f0; font-weight: 700; letter-spacing: 0.8px; margin-top: 8px; padding-top: 6px; border: 1px solid #343a40; border-radius: 5px; background: #181b1f; }
                QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 5px; }
                QGroupBox#panel-pipeline { background: #17202a; border-color: #2d3b4a; }
                QGroupBox#panel-shuffle { background: #1b1b1b; border-color: #373737; }
                QGroupBox#panel-image { background: #17231d; border-color: #2c4538; }
                QGroupBox#panel-watermark { background: #171d24; border-color: #304050; }
                QGroupBox#panel-text { background: #201a27; border-color: #3f344b; }
                QGroupBox#panel-highlight { background: #252014; border-color: #4a3e25; }
                QGroupBox#panel-sticker { background: #142321; border-color: #294845; }
                QGroupBox#panel-export { background: #1b1b1d; border-color: #383a3d; }
                QPushButton, QComboBox, QSpinBox, QDoubleSpinBox { min-height: 28px; max-height: 32px; }
                QTextEdit, QListWidget { border: 1px solid #333; border-radius: 3px; }
                QCheckBox, QRadioButton { min-height: 22px; }
                """
            )
else:
    class WorkflowPanel:  # type: ignore[no-redef]
        pass
