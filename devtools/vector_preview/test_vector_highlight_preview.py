from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from highlight.vector_templates import BlueTagVectorHighlight, OrangeQuoteVectorHighlight


class VectorSandbox(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Vector Highlight Preview Sandbox")
        self.resize(1200, 760)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 1000, 620)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setBackgroundBrush(Qt.white)

        self.template_combo = QComboBox()
        self.template_combo.addItems(["Blue Tag Vector", "Orange Quote Vector"])
        self.text_input = QLineEdit("SALE")
        self.font_size = QSpinBox(); self.font_size.setRange(16, 180); self.font_size.setValue(56)
        self.scale_slider = QSlider(Qt.Horizontal); self.scale_slider.setRange(40, 260); self.scale_slider.setValue(100)
        self.debug_toggle = QCheckBox("Show Debug Bounding Boxes")
        self.export_button = QPushButton("Export Transparent PNG")

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Template")); controls.addWidget(self.template_combo)
        controls.addWidget(QLabel("Text")); controls.addWidget(self.text_input, 1)
        controls.addWidget(QLabel("Font")); controls.addWidget(self.font_size)
        controls.addWidget(QLabel("Scale")); controls.addWidget(self.scale_slider)
        controls.addWidget(self.debug_toggle)
        controls.addWidget(self.export_button)

        root = QVBoxLayout()
        root.addLayout(controls)
        root.addWidget(self.view, 1)

        cw = QWidget(); cw.setLayout(root)
        self.setCentralWidget(cw)

        self.current_item = None
        self._set_item("Blue Tag Vector")

        self.template_combo.currentTextChanged.connect(self._set_item)
        self.text_input.textChanged.connect(self._on_text)
        self.font_size.valueChanged.connect(self._on_font)
        self.scale_slider.valueChanged.connect(self._on_scale)
        self.debug_toggle.toggled.connect(self._on_debug)
        self.export_button.clicked.connect(self._export_png)

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _set_item(self, name: str) -> None:
        old_pos = None
        old_scale = 1.0
        if self.current_item is not None:
            old_pos = self.current_item.pos()
            old_scale = self.current_item.scale()
            self.scene.removeItem(self.current_item)
        if name == "Orange Quote Vector":
            item = OrangeQuoteVectorHighlight(self.text_input.text(), self.font_size.value())
        else:
            item = BlueTagVectorHighlight(self.text_input.text(), self.font_size.value())
        item.setDebug = None
        item.setPos(old_pos if old_pos is not None else self.scene.sceneRect().center())
        item.setScale(old_scale)
        item.set_debug_boxes(self.debug_toggle.isChecked())
        self.scene.addItem(item)
        self.current_item = item

    def _on_text(self, text: str) -> None:
        if self.current_item:
            self.current_item.set_text(text)

    def _on_font(self, size: int) -> None:
        if self.current_item:
            self.current_item.set_font_size(size)

    def _on_scale(self, value: int) -> None:
        if self.current_item:
            self.current_item.setScale(value / 100.0)

    def _on_debug(self, enabled: bool) -> None:
        if self.current_item:
            self.current_item.set_debug_boxes(enabled)

    def _tick(self) -> None:
        if isinstance(self.current_item, OrangeQuoteVectorHighlight):
            self.current_item.step_animation(1.0)

    def _export_png(self) -> None:
        if not self.current_item:
            return
        out = Path("devtools/vector_preview/output/vector_preview.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        self.current_item.export_png(str(out))
        self.statusBar().showMessage(f"Exported: {out}", 4000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = VectorSandbox()
    win.show()
    sys.exit(app.exec())
