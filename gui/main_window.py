"""Main desktop window for the unified app."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import QThread, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QStatusBar, QTextEdit, QVBoxLayout, QWidget
except ImportError:
    QThread = QUrl = Signal = QDesktopServices = QHBoxLayout = QMainWindow = QPushButton = QStatusBar = QTextEdit = QVBoxLayout = QWidget = None

from core.renderer.batch_renderer import BatchRenderer
from gui.preview_canvas import PreviewCanvas
from gui.queue_panel import QueuePanel
from gui.workflow_panel import WorkflowPanel
from models.project_state import ProjectState
from models.sticker_overlay import StickerOverlay
from utils.file_helper import output_directory


if QMainWindow:
    class RenderThread(QThread):
        progress = Signal(int, int, str)
        log = Signal(str)
        failed = Signal(str)
        finishedPaths = Signal(list)

        def __init__(self, state: ProjectState) -> None:
            super().__init__()
            self.state = state

        def run(self) -> None:
            try:
                outputs = BatchRenderer().render(
                    self.state,
                    lambda i, t, m: self.progress.emit(i, t, m),
                    lambda message: self.log.emit(message),
                )
            except Exception as exc:
                self.failed.emit(str(exc))
                return
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
            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)
            self.log_box.setMinimumHeight(160)
            self.log_box.setPlaceholderText("Log tiến trình render sẽ hiển thị tại đây...")
            self.status = QStatusBar()
            self.setStatusBar(self.status)
            self._wire()
            root = QWidget(); layout = QHBoxLayout(root)
            layout.addWidget(self.queue, 1); layout.addWidget(self.preview, 2)
            right = QVBoxLayout()
            right.addWidget(self.workflow)
            right.addWidget(self.export_button)
            right.addWidget(self.open_output_button)
            right.addWidget(self.log_box)
            layout.addLayout(right, 1)
            self.setCentralWidget(root)

        def _wire(self) -> None:
            self.queue.changed.connect(self.set_videos)
            self.workflow.imagePoolSelected.connect(self.set_image_pool)
            self.workflow.stickerSelected.connect(self.set_sticker)
            self.workflow.textChanged.connect(self.set_text)
            self.export_button.clicked.connect(self.render)
            self.open_output_button.clicked.connect(self.open_output_folder)

        def open_output_folder(self) -> None:
            output_path = output_directory(self.state.export.output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            self.append_log(f"Mở thư mục output: {output_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def set_videos(self, paths: list[Path]) -> None:
            self.state.videos = paths
            self.export_button.setText(self.state.render_count_label())
            self.append_log(f"Đã cập nhật queue: {len(paths)} video")

        def set_image_pool(self, paths: list[Path]) -> None:
            self.state.image_composite.image_pool = paths
            self.state.image_composite.enabled = bool(paths)
            self.workflow.image_composite.setChecked(bool(paths))
            self.append_log(f"Đã chọn image pool: {len(paths)} ảnh")

        def set_sticker(self, path: str) -> None:
            self.state.overlays.sticker = StickerOverlay(path=Path(path))
            self.state.overlays.sticker_enabled = True
            self.workflow.sticker_overlay.setChecked(True)
            self.append_log(f"Đã chọn sticker: {Path(path).name}")

        def set_text(self, text: str) -> None:
            self.state.overlays.text.text = text
            active = bool(text.strip())
            self.state.overlays.text_enabled = active
            self.workflow.text_overlay.setChecked(active)
            self.append_log("Text overlay: bật" if active else "Text overlay: tắt")

        def sync_state_from_controls(self) -> None:
            self.state.scene_shuffle.enabled = self.workflow.scene_shuffle.isChecked()
            self.state.image_composite.enabled = self.workflow.image_composite.isChecked() and bool(self.state.image_composite.image_pool)
            self.state.overlays.text_enabled = self.workflow.text_overlay.isChecked() and bool(self.state.overlays.text.text.strip())
            self.state.overlays.sticker_enabled = self.workflow.sticker_overlay.isChecked() and self.state.overlays.sticker.path is not None
            self.state.overlays.text.template = self.workflow.template.currentText()
            self.state.overlays.text.font_size = self.workflow.font_size.value()

        def append_log(self, message: str) -> None:
            self.log_box.append(message)

        def render(self) -> None:
            self.sync_state_from_controls()
            self.export_button.setEnabled(False)
            self.append_log(f"Bắt đầu render batch vào: {output_directory(self.state.export.output_dir).resolve()}")
            self.thread = RenderThread(self.state)
            self.thread.progress.connect(lambda _i, _t, msg: self.status.showMessage(msg))
            self.thread.log.connect(self.append_log)
            self.thread.failed.connect(self.render_failed)
            self.thread.finishedPaths.connect(self.render_finished)
            self.thread.start()

        def render_finished(self, paths: list[str]) -> None:
            self.export_button.setEnabled(True)
            self.status.showMessage(f"Hoàn tất {len(paths)} video")
            self.append_log(f"Hoàn tất {len(paths)} video.")

        def render_failed(self, message: str) -> None:
            self.export_button.setEnabled(True)
            self.status.showMessage("Render lỗi")
            self.append_log("LỖI: " + message)
else:
    class MainWindow:  # type: ignore[no-redef]
        pass
