"""Main desktop window for the unified app."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QThread, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QScrollArea, QSplitter, QStatusBar, QTextEdit, QVBoxLayout, QWidget
except ImportError:
    Qt = QThread = QUrl = Signal = QDesktopServices = QHBoxLayout = QMainWindow = QPushButton = QScrollArea = QSplitter = QStatusBar = QTextEdit = QVBoxLayout = QWidget = None

from core.renderer.batch_renderer import BatchRenderer
from core.renderer.preview_renderer import PreviewRenderer
from gui.preview_canvas import PreviewCanvas
from gui.queue_panel import QueuePanel
from gui.workflow_panel import WorkflowPanel
from models.overlay import MotionPreset
from models.project_state import ProjectState, WorkflowMode
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
            self.renderer = BatchRenderer()

        def stop(self) -> None:
            self.renderer.stop()

        def run(self) -> None:
            try:
                outputs = self.renderer.render(
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
            self.stop_button = QPushButton("Stop")
            self.stop_button.setEnabled(False)
            self.open_output_button = QPushButton("Open Output Folder")
            self.preview_renderer = PreviewRenderer()
            self.preview_cache_dir = Path(tempfile.gettempdir()) / "autovideoaff_preview"
            self.preview_cache_dir.mkdir(parents=True, exist_ok=True)
            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)
            self.log_box.setMinimumHeight(140)
            self.log_box.setMaximumHeight(220)
            self.log_box.setPlaceholderText("Log tiến trình render sẽ hiển thị tại đây...")
            self.status = QStatusBar()
            self.setStatusBar(self.status)
            self._wire()
            root = QWidget(); layout = QHBoxLayout(root)
            left_splitter = QSplitter(Qt.Vertical)
            left_splitter.setMinimumWidth(280)
            left_splitter.setMaximumWidth(340)
            left_splitter.addWidget(self.queue)
            left_splitter.addWidget(self.log_box)
            left_splitter.setSizes([700, 240])

            workflow_container = QWidget()
            right = QVBoxLayout(workflow_container)
            right.addWidget(self.workflow)
            right.addWidget(self.export_button)
            right.addWidget(self.stop_button)
            right.addWidget(self.open_output_button)
            right.addStretch()
            right_scroll = QScrollArea()
            right_scroll.setWidgetResizable(True)
            right_scroll.setMinimumWidth(360)
            right_scroll.setMaximumWidth(420)
            right_scroll.setWidget(workflow_container)

            layout.addWidget(left_splitter, 0)
            layout.addWidget(self.preview, 1)
            layout.addWidget(right_scroll, 0)
            self.setCentralWidget(root)

        def _wire(self) -> None:
            self.queue.changed.connect(self.set_videos)
            self.queue.currentPathChanged.connect(lambda path: self.update_preview(Path(path)))
            self.workflow.imagePoolSelected.connect(self.set_image_pool)
            self.workflow.stickerSelected.connect(self.set_sticker)
            self.workflow.stickerControlsChanged.connect(self.set_sticker_controls)
            self.workflow.textChanged.connect(self.set_text)
            self.workflow.safeAreaChanged.connect(self.set_safe_area_options)
            self.workflow.changed.connect(self.sync_preview_panel_state)
            self.preview.overlayMoved.connect(self.set_overlay_position)
            self.export_button.clicked.connect(self.render)
            self.stop_button.clicked.connect(self.stop_render)
            self.open_output_button.clicked.connect(self.open_output_folder)


        def set_safe_area_options(self, platform: str, enabled: bool, snap_enabled: bool) -> None:
            self.state.safe_area.platform = platform
            self.state.safe_area.enabled = enabled
            self.state.safe_area.snap_enabled = snap_enabled
            self.preview.set_safe_area_options(platform, enabled, snap_enabled)

        def sync_preview_panel_state(self) -> None:
            mode = self.workflow.selected_workflow_mode()
            overlay_pipeline = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4}
            self.preview.set_overlay_active("text", overlay_pipeline and bool(self.state.overlays.text.text.strip()))
            self.preview.set_overlay_active("sticker", overlay_pipeline and self.state.overlays.sticker.path is not None)

        def open_output_folder(self) -> None:
            output_path = output_directory(self.state.export.output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            self.append_log(f"[INFO] Mở thư mục output: {output_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def set_videos(self, paths: list[Path]) -> None:
            self.state.videos = paths
            self.export_button.setText(self.state.render_count_label())
            self.append_log(f"[INFO] Loading videos: {len(paths)} video")
            if paths:
                self.update_preview(paths[0])

        def set_image_pool(self, paths: list[Path]) -> None:
            self.state.image_composite.image_pool = paths
            self.state.image_composite.enabled = bool(paths)
            self.workflow.set_image_pool(paths)
            self.append_log(f"[INFO] Đã chọn image pool: {len(paths)} ảnh")

        def set_sticker(self, path: str) -> None:
            self.state.overlays.sticker = StickerOverlay(path=Path(path))
            self.set_sticker_controls(
                float(self.workflow.sticker_scale.value()),
                float(self.workflow.sticker_rotation.value()),
                self.workflow.sticker_motion.currentText(),
            )
            self.state.overlays.sticker_enabled = True
            self.preview.set_overlay_active("sticker", True)
            self.preview.set_overlay_position("sticker", self.state.overlays.sticker.x, self.state.overlays.sticker.y)
            self.append_log(f"[INFO] Đã chọn sticker: {Path(path).name}")

        def set_sticker_controls(self, scale: float, rotation: float, motion: str) -> None:
            self.state.overlays.sticker.scale = scale
            self.state.overlays.sticker.rotation = rotation
            self.state.overlays.sticker.motion = MotionPreset.from_label(motion)
            self.preview.set_overlay_active("sticker", self.state.overlays.sticker.active)
            self.preview.update()

        def set_overlay_position(self, kind: str, x: float, y: float) -> None:
            if kind == "text":
                self.state.overlays.text.x = x
                self.state.overlays.text.y = y
            elif kind == "sticker":
                self.state.overlays.sticker.x = x
                self.state.overlays.sticker.y = y

        def set_text(self, text: str) -> None:
            self.state.overlays.text.text = text
            active = bool(text.strip())
            self.state.overlays.text_enabled = active
            self.preview.set_overlay_active("text", active)
            self.preview.set_overlay_position("text", self.state.overlays.text.x, self.state.overlays.text.y)
            # Keep typing workflow quiet; render logs will show overlay processing when enabled.

        def update_preview(self, video_path: Path) -> None:
            if not video_path.exists():
                self.append_log(f"[WARNING] Không tìm thấy video preview: {video_path}")
                return
            cache_name = hashlib.sha1(str(video_path).encode("utf-8")).hexdigest() + ".jpg"
            preview_path = self.preview_cache_dir / cache_name
            try:
                if not preview_path.exists():
                    self.preview_renderer.extract_first_valid_frame(video_path, preview_path)
                self.preview.set_preview_image(preview_path)
            except Exception as exc:
                self.append_log(f"[WARNING] Không tạo được preview: {exc}")

        def sync_state_from_controls(self) -> None:
            mode = self.workflow.selected_workflow_mode()
            self.state.workflow_mode = mode
            self.state.scene_shuffle.enabled = mode in {WorkflowMode.PIPELINE_1, WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3}
            self.state.scene_shuffle.sensitivity = float(self.workflow.scene_sensitivity.value())
            self.state.scene_shuffle.random_mode = True
            self.state.scene_shuffle.keep_first_segment = True
            self.state.scene_shuffle.fallback_min_seconds = float(self.workflow.fallback_min.value())
            self.state.scene_shuffle.fallback_max_seconds = max(float(self.workflow.fallback_max.value()), float(self.workflow.fallback_min.value()))
            self.state.image_composite.enabled = mode in {WorkflowMode.PIPELINE_1, WorkflowMode.PIPELINE_2} and bool(self.state.image_composite.image_pool)
            self.state.image_composite.image_height_percent = float(self.workflow.image_height.value())
            self.state.image_composite.overlap_percent = min(float(self.workflow.overlap.value()), self.state.image_composite.image_height_percent)
            self.state.image_composite.crop_focus = self.workflow.crop_focus.currentText()
            self.state.image_composite.fade_curve = self.workflow.fade_curve.currentText()
            self.set_safe_area_options(
                self.workflow.safe_platform.currentText(),
                self.workflow.safe_area_toggle.isChecked(),
                self.workflow.snap_toggle.isChecked(),
            )
            overlay_pipeline = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4}
            self.state.overlays.text_enabled = overlay_pipeline and bool(self.state.overlays.text.text.strip())
            self.state.overlays.sticker_enabled = overlay_pipeline and self.state.overlays.sticker.path is not None
            self.state.overlays.text.template = self.workflow.template.currentText()
            self.state.overlays.text.font_size = self.workflow.font_size.value()
            self.state.overlays.text.motion = MotionPreset.from_label(self.workflow.motion.currentText())
            self.set_sticker_controls(
                float(self.workflow.sticker_scale.value()),
                float(self.workflow.sticker_rotation.value()),
                self.workflow.sticker_motion.currentText(),
            )

        def append_log(self, message: str) -> None:
            self.log_box.append(message)

        def render(self) -> None:
            self.sync_state_from_controls()
            self.export_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.export_button.setText("Rendering...")
            self.append_log(f"[INFO] Bắt đầu render batch vào: {output_directory(self.state.export.output_dir).resolve()}")
            self.thread = RenderThread(self.state)
            self.thread.progress.connect(self.render_progress)
            self.thread.log.connect(self.append_log)
            self.thread.failed.connect(self.render_failed)
            self.thread.finishedPaths.connect(self.render_finished)
            self.thread.start()

        def render_progress(self, index: int, total: int, message: str) -> None:
            self.status.showMessage(message)
            self.export_button.setText(f"Rendering... {index}/{total}")

        def stop_render(self) -> None:
            if hasattr(self, "thread"):
                self.thread.stop()
                self.append_log("[WARNING] Stop requested — terminating FFmpeg tasks...")

        def render_finished(self, paths: list[str]) -> None:
            self.export_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.export_button.setText("Render Complete")
            self.status.showMessage(f"Hoàn tất {len(paths)} video")
            self.append_log(f"[SUCCESS] Hoàn tất {len(paths)} video.")
            if self.state.export.auto_open_output:
                self.open_output_folder()

        def render_failed(self, message: str) -> None:
            self.export_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.export_button.setText(self.state.render_count_label())
            self.status.showMessage("Render lỗi")
            self.append_log("[ERROR] " + message)
else:
    class MainWindow:  # type: ignore[no-redef]
        pass
