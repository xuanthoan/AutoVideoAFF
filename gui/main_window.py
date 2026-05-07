"""Main desktop window for the unified app."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import QThread, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QStatusBar, QVBoxLayout, QWidget
except ImportError:
    QThread = QUrl = Signal = QDesktopServices = QHBoxLayout = QMainWindow = QPushButton = QStatusBar = QVBoxLayout = QWidget = None

from core.renderer.batch_renderer import BatchRenderer
from gui.preview_canvas import PreviewCanvas
from gui.queue_panel import QueuePanel
from gui.workflow_panel import WorkflowPanel
from models.project_state import ProjectState
from models.sticker_overlay import StickerOverlay


if QMainWindow:
    class RenderThread(QThread):
        progress = Signal(int, int, str)
        finishedPaths = Signal(list)

        def __init__(self, state: ProjectState) -> None:
            super().__init__()
            self.state = state

        def run(self) -> None:
            outputs = BatchRenderer().render(self.state, lambda i, t, m: self.progress.emit(i, t, m))
            self.finishedPaths.emit(outputs)


    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AutoVideoAFF — Unified Mass Video Production")
            self.state = ProjectState()
            self.queue = QueuePanel()
            self.preview = PreviewCanvas()
            self.workflow = WorkflowPanel()
            self.export_button = QPushButton(self.state.render_count_label())
            self.open_output_button = QPushButton("Mở thư mục output")
            self.status = QStatusBar()
            self.setStatusBar(self.status)
            self._wire()
            root = QWidget(); layout = QHBoxLayout(root)
            layout.addWidget(self.queue, 1); layout.addWidget(self.preview, 2)
            right = QVBoxLayout(); right.addWidget(self.workflow); right.addWidget(self.export_button); right.addWidget(self.open_output_button)
            layout.addLayout(right, 1)
            self.setCentralWidget(root)

        def _wire(self) -> None:
            self.queue.changed.connect(self.set_videos)
            self.workflow.imagePoolSelected.connect(self.set_image_pool)
            self.workflow.stickerSelected.connect(self.set_sticker)
            self.workflow.textChanged.connect(self.set_text)
            self.export_button.clicked.connect(self.render)
            self.open_output_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.state.export.output_dir.resolve()))))

        def set_videos(self, paths: list[Path]) -> None:
            self.state.videos = paths
            self.export_button.setText(self.state.render_count_label())

        def set_image_pool(self, paths: list[Path]) -> None:
            self.state.image_composite.image_pool = paths
            self.state.image_composite.enabled = bool(paths)
            self.workflow.image_composite.setChecked(bool(paths))

        def set_sticker(self, path: str) -> None:
            self.state.overlays.sticker = StickerOverlay(path=Path(path))
            self.state.overlays.sticker_enabled = True
            self.workflow.sticker_overlay.setChecked(True)

        def set_text(self, text: str) -> None:
            self.state.overlays.text.text = text
            self.state.overlays.text_enabled = bool(text.strip())
            self.workflow.text_overlay.setChecked(bool(text.strip()))

        def sync_state_from_controls(self) -> None:
            self.state.scene_shuffle.enabled = self.workflow.scene_shuffle.isChecked()
            self.state.image_composite.enabled = self.workflow.image_composite.isChecked() and bool(self.state.image_composite.image_pool)
            self.state.overlays.text_enabled = self.workflow.text_overlay.isChecked() and bool(self.state.overlays.text.text.strip())
            self.state.overlays.sticker_enabled = self.workflow.sticker_overlay.isChecked() and self.state.overlays.sticker.path is not None
            self.state.overlays.text.template = self.workflow.template.currentText()
            self.state.overlays.text.font_size = self.workflow.font_size.value()

        def render(self) -> None:
            self.sync_state_from_controls()
            self.export_button.setEnabled(False)
            self.thread = RenderThread(self.state)
            self.thread.progress.connect(lambda _i, _t, msg: self.status.showMessage(msg))
            self.thread.finishedPaths.connect(lambda _paths: self.export_button.setEnabled(True))
            self.thread.start()
else:
    class MainWindow:  # type: ignore[no-redef]
        pass
