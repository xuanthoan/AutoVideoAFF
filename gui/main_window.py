"""Main desktop window for the unified app."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QThread, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QPushButton, QScrollArea, QSplitter, QStatusBar, QTextEdit, QVBoxLayout, QWidget
except ImportError:
    Qt = QThread = QUrl = Signal = QDesktopServices = QFileDialog = QHBoxLayout = QMainWindow = QPushButton = QScrollArea = QSplitter = QStatusBar = QTextEdit = QVBoxLayout = QWidget = None

from core.pipeline.shuffle_pipeline import SceneShufflePipeline
from core.overlays.watermark_engine import WatermarkLayoutEngine
from core.renderer.batch_renderer import BatchRenderer
from core.renderer.preview_renderer import PreviewRenderer
from core.video.scene_detector import SceneDetector
from core.video.segmenter import Segmenter
from gui.mini_timeline import MiniTimeline, SegmentTimelineItem, TimelineOverlayItem
from gui.preview_canvas import PreviewCanvas
from gui.queue_panel import QueuePanel
from gui.workflow_panel import WorkflowPanel
from models.overlay import MotionPreset
from models.project_state import ProjectState, TimelineSegment, WorkflowMode
from models.sticker_overlay import StickerOverlay
from utils.ffmpeg_helper import FFmpegNotFoundError, probe_duration
from utils.file_helper import output_directory_for_videos


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
            self.timeline = MiniTimeline()
            self.video_duration = 6.0
            self.current_video_path: Path | None = None
            self.workflow = WorkflowPanel()
            self.export_button = QPushButton("Render Video")
            self.stop_button = QPushButton("Stop")
            self.stop_button.setEnabled(False)
            self.open_output_button = QPushButton("Open Output Folder")
            self.workflow.set_export_controls(self.export_button, self.stop_button, self.open_output_button)
            self.preview_renderer = PreviewRenderer()
            self.watermark_layout = WatermarkLayoutEngine()
            self.preview_cache_dir = Path(tempfile.gettempdir()) / "autovideoaff_preview"
            self.preview_cache_dir.mkdir(parents=True, exist_ok=True)
            self.preview_frame_fps = 6
            self._last_preview_frame_key: tuple[str, int] | None = None
            self.manual_cut_undo_stack: list[list[TimelineSegment]] = []
            self.manual_cut_redo_stack: list[list[TimelineSegment]] = []
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
            left_splitter.setMinimumWidth(220)
            left_splitter.setMaximumWidth(320)
            left_splitter.addWidget(self.queue)
            left_splitter.addWidget(self.log_box)
            left_splitter.setSizes([700, 240])

            workflow_container = QWidget()
            workflow_layout = QVBoxLayout(workflow_container)
            workflow_layout.setContentsMargins(4, 4, 4, 4)
            workflow_layout.setSpacing(4)
            workflow_layout.addWidget(self.workflow)
            workflow_layout.addStretch()
            right_scroll = QScrollArea()
            right_scroll.setWidgetResizable(True)
            right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            right_scroll.setWidget(workflow_container)

            right_column = QWidget()
            right_column.setMinimumWidth(500)
            right_column.setMaximumWidth(620)
            right_column_layout = QVBoxLayout(right_column)
            right_column_layout.setContentsMargins(0, 0, 0, 0)
            right_column_layout.setSpacing(6)
            right_column_layout.addWidget(right_scroll, 1)

            center_column = QWidget()
            center_layout = QVBoxLayout(center_column)
            center_layout.setContentsMargins(0, 0, 0, 0)
            center_layout.setSpacing(6)
            center_layout.addWidget(self.preview, 1)
            center_layout.addWidget(self.timeline, 0)

            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(8)
            layout.addWidget(left_splitter, 16)
            layout.addWidget(center_column, 56)
            layout.addWidget(right_column, 28)
            self.setCentralWidget(root)

        def _wire(self) -> None:
            self.queue.changed.connect(self.set_videos)
            self.queue.currentPathChanged.connect(lambda path: (self.set_video_duration(Path(path)), self.update_preview(Path(path))))
            self.workflow.imagePoolSelected.connect(self.set_image_pool)
            self.workflow.stickerSelected.connect(self.set_sticker)
            self.workflow.stickerControlsChanged.connect(self.set_sticker_controls)
            self.workflow.textChanged.connect(self.set_text)
            self.workflow.watermark_enabled.toggled.connect(lambda _checked: self.update_watermark_preview())
            self.workflow.watermark_text.textChanged.connect(self.on_watermark_text_changed)
            self.workflow.watermark_font.currentTextChanged.connect(lambda _text: self.update_watermark_preview())
            self.workflow.watermark_font_size.valueChanged.connect(lambda _value: self.update_watermark_preview())
            self.workflow.watermark_color.currentTextChanged.connect(lambda _text: self.update_watermark_preview())
            self.workflow.watermark_opacity.valueChanged.connect(lambda _value: self.update_watermark_preview())
            self.workflow.watermark_density.currentTextChanged.connect(lambda _text: self.update_watermark_preview())
            self.workflow.template.currentTextChanged.connect(lambda _text: self.update_text_preview())
            self.workflow.font_size.valueChanged.connect(lambda _value: self.update_text_preview())
            self.workflow.motion.currentTextChanged.connect(lambda _text: self.update_text_preview())
            self.workflow.text_motion_speed.currentTextChanged.connect(lambda _text: self.update_text_preview())
            self.workflow.text_motion_strength.valueChanged.connect(lambda _value: self.update_text_preview())
            self.workflow.highlight_enabled.toggled.connect(lambda _checked: (self.update_highlight_preview(), self.refresh_timeline()))
            self.workflow.highlight_text.textChanged.connect(self.on_highlight_text_changed)
            self.workflow.highlight_font_size.valueChanged.connect(lambda _value: self.update_highlight_preview())
            self.workflow.highlight_style.currentTextChanged.connect(lambda _text: self.update_highlight_preview())
            self.workflow.highlight_animation.currentTextChanged.connect(lambda _text: self.update_highlight_preview())
            self.workflow.changed.connect(self.sync_preview_panel_state)
            self.preview.previewMotionDebug.connect(self.append_log)
            self.preview.overlayMoved.connect(self.set_overlay_position)
            self.timeline.playheadChanged.connect(self.set_playhead_time)
            self.timeline.overlayTimingChanged.connect(self.set_overlay_timing)
            self.timeline.overlaySelected.connect(self.select_overlay)
            self.timeline.overlayVisibilityChanged.connect(self.set_overlay_visibility)
            self.timeline.generateAutoSegmentsRequested.connect(self.generate_auto_segments)
            self.timeline.addCutRequested.connect(self.add_cut_at_time)
            self.timeline.previewShuffleOrderRequested.connect(self.preview_shuffle_order)
            self.timeline.saveTimelineRequested.connect(self.save_timeline)
            self.timeline.loadTimelineRequested.connect(self.load_timeline)
            self.timeline.segmentEnabledChanged.connect(self.set_segment_enabled)
            self.timeline.segmentLockedChanged.connect(self.set_segment_locked)
            self.timeline.removeSegmentRequested.connect(self.remove_segment)
            self.timeline.undoCutRequested.connect(self.undo_manual_cut)
            self.timeline.redoCutRequested.connect(self.redo_manual_cut)
            self.timeline.clearManualCutsRequested.connect(self.clear_manual_cuts)
            self.export_button.clicked.connect(self.render)
            self.stop_button.clicked.connect(self.stop_render)
            self.open_output_button.clicked.connect(self.open_output_folder)


        def set_safe_area_options(self, platform: str = "TikTok", enabled: bool = True, snap_enabled: bool = True) -> None:
            self.state.safe_area.platform = platform
            self.state.safe_area.enabled = enabled
            self.state.safe_area.snap_enabled = snap_enabled
            self.preview.set_safe_area_options(platform, enabled, snap_enabled)

        def sync_preview_panel_state(self) -> None:
            mode = self.workflow.selected_workflow_mode()
            overlay_pipeline = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4}
            self.update_watermark_preview()
            self.update_text_preview()
            self.update_highlight_preview()
            self.update_sticker_preview()
            self.update_watermark_preview()

        def open_output_folder(self) -> None:
            output_path = output_directory_for_videos(self.state.videos, self.state.export.output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            self.append_log(f"[INFO] Mở thư mục output: {output_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def set_videos(self, paths: list[Path]) -> None:
            self.state.videos = paths
            self.export_button.setText("Render Video")
            self.append_log(f"[INFO] Loading videos: {len(paths)} video")
            if paths:
                self.set_video_duration(paths[0])
                self.update_preview(paths[0])
            else:
                self.video_duration = 6.0
                self.timeline.set_duration(self.video_duration)

        def set_image_pool(self, paths: list[Path]) -> None:
            self.state.image_composite.image_pool = paths
            self.state.image_composite.enabled = bool(paths)
            self.workflow.set_image_pool(paths)
            self.append_log(f"[INFO] Đã chọn image pool: {len(paths)} ảnh")

        def set_sticker(self, path: str) -> None:
            self.state.overlays.sticker = StickerOverlay(path=Path(path))
            self.state.overlays.sticker.set_full_duration(self.video_duration)
            self.update_highlight_preview()
            self.update_watermark_preview()
            self.set_sticker_controls(
                float(self.workflow.sticker_scale.value()),
                float(self.workflow.sticker_rotation.value()),
                self.workflow.sticker_motion.currentText(),
            )
            self.state.overlays.sticker_enabled = True
            self.update_sticker_preview()
            self.refresh_timeline()
            self.append_log(f"[INFO] Đã chọn sticker: {Path(path).name}")

        def set_sticker_controls(self, scale: float, rotation: float, motion: str) -> None:
            self.state.overlays.sticker.scale = scale
            self.state.overlays.sticker.rotation = rotation
            self.state.overlays.sticker.motion = MotionPreset.from_label(motion)
            self.state.overlays.sticker.motion_speed = self.workflow.sticker_motion_speed_ratio()
            self.state.overlays.sticker.motion_strength = self.workflow.motion_strength_ratio(self.workflow.sticker_motion_strength)
            self.update_sticker_preview()

        def set_overlay_position(self, kind: str, x: float, y: float) -> None:
            if kind == "text":
                self.state.overlays.text.x = x
                self.state.overlays.text.y = y
            elif kind == "highlight":
                self.state.overlays.highlight.x = x
                self.state.overlays.highlight.y = y
            elif kind == "sticker":
                self.state.overlays.sticker.x = x
                self.state.overlays.sticker.y = y


        def on_watermark_text_changed(self) -> None:
            if self.workflow.watermark_text.toPlainText().strip() and not self.workflow.watermark_enabled.isChecked():
                self.workflow.watermark_enabled.blockSignals(True)
                self.workflow.watermark_enabled.setChecked(True)
                self.workflow.watermark_enabled.blockSignals(False)
            self.update_watermark_preview()

        def on_highlight_text_changed(self) -> None:
            if self.workflow.highlight_text.toPlainText().strip() and not self.workflow.highlight_enabled.isChecked():
                self.workflow.highlight_enabled.blockSignals(True)
                self.workflow.highlight_enabled.setChecked(True)
                self.workflow.highlight_enabled.blockSignals(False)
            self.update_highlight_preview()
            self.refresh_timeline()

        def update_watermark_preview(self) -> None:
            watermark = self.state.overlays.watermark
            watermark.text = self.workflow.watermark_text.toPlainText().strip()
            watermark.font_family = self.workflow.watermark_font.currentText()
            watermark.set_font_size(self.workflow.watermark_font_size.value())
            watermark.font_color = self.workflow.watermark_color.currentText()
            watermark.opacity_percent = int(self.workflow.watermark_opacity.value())
            watermark.rotation = -15.0
            watermark.random_position = True
            watermark.slow_floating_motion = True
            watermark.density = self.workflow.watermark_density.currentText()  # type: ignore[assignment]
            watermark.enabled = self.workflow.watermark_enabled.isChecked()
            self.state.overlays.watermark_enabled = watermark.active
            if watermark.active:
                watermark.instances = self.watermark_layout.generate(self.state.overlays, seed=self._current_watermark_seed())
            self.preview.set_watermark_overlay(watermark, watermark.active)

        def _current_watermark_seed(self) -> int:
            source = str(self.current_video_path.resolve() if self.current_video_path else "preview")
            return int(hashlib.sha1(source.encode("utf-8")).hexdigest()[:12], 16)


        def update_text_preview(self) -> None:
            self.state.overlays.text.template = self.workflow.template.currentText()
            self.state.overlays.text.set_font_size(self.workflow.font_size.value())
            self.state.overlays.text.motion = MotionPreset.from_label(self.workflow.motion.currentText())
            self.state.overlays.text.motion_speed = self.workflow.text_motion_speed_ratio()
            self.state.overlays.text.motion_strength = self.workflow.motion_strength_ratio(self.workflow.text_motion_strength)
            mode = self.workflow.selected_workflow_mode()
            active = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4} and self.state.overlays.text.active
            self.preview.set_text_overlay(
                self.state.overlays.text.text,
                self.state.overlays.text.template,
                self.state.overlays.text.effective_font_ratio(),
                active,
                self.state.overlays.text.motion.value,
                self.state.overlays.text.motion_speed,
                self.state.overlays.text.motion_strength,
            )
            self.preview.set_overlay_timing("text", self.state.overlays.text.start_time, self.state.overlays.text.end_time)
            self.preview.set_overlay_position("text", self.state.overlays.text.x, self.state.overlays.text.y)
            self.update_watermark_preview()


        def update_highlight_preview(self) -> None:
            highlight = self.state.overlays.highlight
            highlight.text = self.workflow.highlight_text.toPlainText().strip()
            highlight.style = self.workflow.highlight_style.currentText()
            highlight.set_font_size(self.workflow.highlight_font_size.value())
            highlight.set_animation_label(self.workflow.highlight_animation.currentText())
            highlight.motion_speed = 1.35
            highlight.motion_strength = 1.45
            mode = self.workflow.selected_workflow_mode()
            active = (
                mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4}
                and self.workflow.highlight_enabled.isChecked()
                and highlight.active
            )
            self.state.overlays.highlight_enabled = active
            self.preview.set_highlight_overlay(
                highlight.text,
                highlight.style,
                highlight.effective_font_ratio(),
                active,
                highlight.motion.value,
                highlight.motion_speed,
                highlight.motion_strength,
            )
            self.preview.set_overlay_timing("highlight", highlight.start_time, highlight.end_time)
            self.preview.set_overlay_position("highlight", highlight.x, highlight.y)
            self.update_watermark_preview()

        def update_sticker_preview(self) -> None:
            mode = self.workflow.selected_workflow_mode()
            active = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4} and self.state.overlays.sticker.active
            self.preview.set_sticker_overlay(
                self.state.overlays.sticker.path,
                self.state.overlays.sticker.scale,
                self.state.overlays.sticker.rotation,
                active,
                self.state.overlays.sticker.motion.value,
                self.state.overlays.sticker.motion_speed,
                self.state.overlays.sticker.motion_strength,
            )
            self.preview.set_overlay_timing("sticker", self.state.overlays.sticker.start_time, self.state.overlays.sticker.end_time)
            self.preview.set_overlay_position("sticker", self.state.overlays.sticker.x, self.state.overlays.sticker.y)
            self.update_watermark_preview()

        def set_playhead_time(self, time_seconds: float) -> None:
            self.timeline.set_playhead_time(time_seconds)
            self.update_preview_frame(time_seconds)
            self.preview.set_playhead_time(time_seconds)
            self.update_watermark_preview()
            self.update_text_preview()
            self.update_highlight_preview()
            self.update_sticker_preview()

        def set_overlay_timing(self, key: str, start: float, end: float) -> None:
            overlay = self._overlay_by_key(key)
            if overlay is None:
                return
            overlay.set_timing(start, end)
            self.preview.set_overlay_timing(key, start, end)
            self.refresh_timeline()
            self.update_watermark_preview()
            self.update_text_preview()
            self.update_highlight_preview()
            self.update_sticker_preview()

        def select_overlay(self, key: str) -> None:
            if key == "text":
                self.workflow.text.setFocus()
            elif key == "highlight":
                self.workflow.highlight_text.setFocus()
            elif key == "sticker":
                self.workflow.sticker_scale.setFocus()
            self.status.showMessage(f"Selected overlay: {key}")

        def set_overlay_visibility(self, key: str, visible: bool) -> None:
            overlay = self._overlay_by_key(key)
            if overlay is None:
                return
            overlay.enabled = visible
            if key == "text":
                self.state.overlays.text_enabled = visible and self.state.overlays.text.active
            elif key == "highlight":
                self.state.overlays.highlight_enabled = visible and self.state.overlays.highlight.active
                self.workflow.highlight_enabled.setChecked(visible)
            elif key == "sticker":
                self.state.overlays.sticker_enabled = visible and self.state.overlays.sticker.active
            self.update_watermark_preview()
            self.update_text_preview()
            self.update_highlight_preview()
            self.update_sticker_preview()
            self.refresh_timeline()

        def _overlay_by_key(self, key: str):
            if key == "text":
                return self.state.overlays.text
            if key == "highlight":
                return self.state.overlays.highlight
            if key == "sticker":
                return self.state.overlays.sticker
            return None

        def refresh_timeline(self) -> None:
            items: list[TimelineOverlayItem] = []
            if self.state.overlays.text.text.strip():
                items.append(
                    TimelineOverlayItem(
                        "text",
                        "text",
                        "Text 1",
                        self.state.overlays.text.start_time,
                        self.state.overlays.text.end_time,
                        self.state.overlays.text.enabled,
                    )
                )
            if self.state.overlays.highlight.text.strip():
                items.append(
                    TimelineOverlayItem(
                        "highlight",
                        "highlight",
                        "Highlight",
                        self.state.overlays.highlight.start_time,
                        self.state.overlays.highlight.end_time,
                        self.state.overlays.highlight.enabled,
                    )
                )
            if self.state.overlays.sticker.path is not None:
                items.append(
                    TimelineOverlayItem(
                        "sticker",
                        "sticker",
                        "Sticker 1",
                        self.state.overlays.sticker.start_time,
                        self.state.overlays.sticker.end_time,
                        self.state.overlays.sticker.enabled,
                    )
                )
            self.timeline.set_duration(self.video_duration)
            self.timeline.set_segments(self._timeline_segment_items())
            self.timeline.set_items(items)

        def set_text(self, text: str) -> None:
            was_inactive = not self.state.overlays.text.active
            self.state.overlays.text.text = text
            if was_inactive and text.strip():
                self.state.overlays.text.set_full_duration(self.video_duration)
            active = bool(text.strip())
            self.state.overlays.text_enabled = active
            self.update_text_preview()
            self.refresh_timeline()
            # Keep typing workflow quiet; render logs will show overlay processing when enabled.

        def set_video_duration(self, video_path: Path) -> None:
            if self.current_video_path != video_path:
                self.manual_cut_undo_stack.clear()
                self.manual_cut_redo_stack.clear()
                self._last_preview_frame_key = None
            self.current_video_path = video_path
            try:
                self.video_duration = max(0.1, probe_duration(video_path))
            except (FFmpegNotFoundError, KeyError, ValueError, OSError) as exc:
                self.video_duration = 6.0
                self.append_log(f"[WARNING] Không đọc được duration, dùng timeline 6s: {exc}")
            self.timeline.set_duration(self.video_duration)
            if not self.state.overlays.text.text.strip():
                self.state.overlays.text.set_full_duration(self.video_duration)
            if not self.state.overlays.highlight.text.strip():
                self.state.overlays.highlight.set_full_duration(self.video_duration)
            if self.state.overlays.sticker.path is None:
                self.state.overlays.sticker.set_full_duration(self.video_duration)
            self.refresh_timeline()
            self.update_watermark_preview()


        def _timeline_segments(self) -> list[TimelineSegment]:
            segment_path = self.state.scene_shuffle.segment_video_path
            if segment_path and self.current_video_path and segment_path != str(self.current_video_path):
                return [TimelineSegment(0.0, self.video_duration, source="auto", enabled=True, locked=False)]
            segments = self.state.scene_shuffle.active_segments()
            if segments:
                return [segment.normalized(self.video_duration) for segment in segments]
            return [TimelineSegment(0.0, self.video_duration, source="auto", enabled=True, locked=False)]

        def _timeline_segment_items(self) -> list[SegmentTimelineItem]:
            return [
                SegmentTimelineItem(segment.start_time, segment.end_time, segment.source, segment.enabled, segment.locked)
                for segment in self._timeline_segments()
            ]

        def _activate_manual_segments(self) -> list[TimelineSegment]:
            if not self.state.scene_shuffle.manual_segments:
                self.state.scene_shuffle.manual_segments = [
                    TimelineSegment(segment.start_time, segment.end_time, "manual", segment.enabled, segment.locked)
                    for segment in self._timeline_segments()
                ]
                self.state.scene_shuffle.segment_video_path = str(self.current_video_path) if self.current_video_path else None
            return self.state.scene_shuffle.manual_segments

        def generate_auto_segments(self) -> None:
            if self.current_video_path is None:
                self.append_log("[WARNING] Chọn video trước khi Generate Auto Segments.")
                return
            detected = SceneDetector().detect(self.current_video_path, float(self.workflow.scene_sensitivity.value()))
            ensured = Segmenter(float(self.workflow.fallback_min.value()), float(self.workflow.fallback_max.value())).ensure_segments(
                detected, self.current_video_path
            )
            self.state.scene_shuffle.auto_segments = [TimelineSegment(item.start, item.end, source="auto") for item in ensured]
            self.state.scene_shuffle.manual_segments = []
            self.manual_cut_undo_stack.clear()
            self.manual_cut_redo_stack.clear()
            self.state.scene_shuffle.segment_video_path = str(self.current_video_path)
            self.refresh_timeline()
            self.append_log(f"[SEGMENTS] Generated {len(self.state.scene_shuffle.auto_segments)} auto segments for current video.")

        def add_cut_at_time(self, time_seconds: float) -> None:
            cut = min(max(float(time_seconds), 0.0), self.video_duration)
            current_segments = self._timeline_segments()
            for index, segment in enumerate(list(current_segments)):
                if segment.start_time + 0.05 < cut < segment.end_time - 0.05:
                    segments = self._activate_manual_segments()
                    self._push_manual_cut_undo()
                    locked = segment.locked
                    enabled = segment.enabled
                    segments[index:index + 1] = [
                        TimelineSegment(segment.start_time, cut, "manual", enabled, locked),
                        TimelineSegment(cut, segment.end_time, "manual", enabled, locked),
                    ]
                    self.refresh_timeline()
                    self.append_log(f"[SEGMENTS] Add Cut at {cut:.2f}s -> manual segment mode active.")
                    return
            self.append_log(f"[WARNING] Không thể add cut tại {cut:.2f}s (quá sát boundary).")

        def set_segment_enabled(self, row: int, enabled: bool) -> None:
            segments = self._activate_manual_segments()
            if 0 <= row < len(segments):
                self._push_manual_cut_undo()
                segments[row].enabled = bool(enabled)
                segments[row].source = "manual"
                self.refresh_timeline()
                self.append_log(f"[SEGMENTS] Segment {row + 1} enabled={enabled}; manual segment mode active.")

        def set_segment_locked(self, row: int, locked: bool) -> None:
            segments = self._activate_manual_segments()
            if 0 <= row < len(segments):
                self._push_manual_cut_undo()
                segments[row].locked = bool(locked)
                segments[row].source = "manual"
                self.refresh_timeline()
                self.append_log(f"[SEGMENTS] Segment {row + 1} locked={locked}; manual segment mode active.")

        def remove_segment(self, row: int) -> None:
            segments = self._activate_manual_segments()
            if 0 <= row < len(segments):
                self._push_manual_cut_undo()
                removed = segments.pop(row)
                self.refresh_timeline()
                self.append_log(f"[SEGMENTS] Removed segment {row + 1} ({removed.start_time:.2f}-{removed.end_time:.2f}); manual segment mode active.")

        def _manual_cut_snapshot(self) -> list[TimelineSegment]:
            return [
                TimelineSegment(segment.start_time, segment.end_time, "manual", segment.enabled, segment.locked)
                for segment in self.state.scene_shuffle.manual_segments
            ]

        def _restore_manual_cut_snapshot(self, snapshot: list[TimelineSegment]) -> None:
            self.state.scene_shuffle.manual_segments = [
                TimelineSegment(segment.start_time, segment.end_time, "manual", segment.enabled, segment.locked)
                for segment in snapshot
            ]
            self.state.scene_shuffle.segment_video_path = str(self.current_video_path) if self.state.scene_shuffle.manual_segments and self.current_video_path else None
            self.refresh_timeline()

        def _push_manual_cut_undo(self) -> None:
            self.manual_cut_undo_stack.append(self._manual_cut_snapshot())
            self.manual_cut_redo_stack.clear()

        def undo_manual_cut(self) -> None:
            if not self.manual_cut_undo_stack:
                self.append_log("[SEGMENTS] Không có manual cut để undo.")
                return
            self.manual_cut_redo_stack.append(self._manual_cut_snapshot())
            self._restore_manual_cut_snapshot(self.manual_cut_undo_stack.pop())
            self.append_log("[SEGMENTS] Undo Cut applied.")

        def redo_manual_cut(self) -> None:
            if not self.manual_cut_redo_stack:
                self.append_log("[SEGMENTS] Không có manual cut để redo.")
                return
            self.manual_cut_undo_stack.append(self._manual_cut_snapshot())
            self._restore_manual_cut_snapshot(self.manual_cut_redo_stack.pop())
            self.append_log("[SEGMENTS] Redo Cut applied.")

        def clear_manual_cuts(self) -> None:
            if not self.state.scene_shuffle.manual_segments:
                self.append_log("[SEGMENTS] Không có manual cuts để clear.")
                return
            self._push_manual_cut_undo()
            self.state.scene_shuffle.manual_segments = []
            self.state.scene_shuffle.segment_video_path = str(self.current_video_path) if self.current_video_path else None
            self.refresh_timeline()
            self.append_log("[SEGMENTS] Cleared manual cuts; Auto Scene Detect mode is active when auto segments are available.")

        def preview_shuffle_order(self) -> None:
            segments = [segment for segment in self._timeline_segments() if segment.enabled]
            ordered = SceneShufflePipeline(random=None)._shuffle_segments(
                segments, True, self.state.scene_shuffle.keep_first_segment
            )
            order = ", ".join(f"{segment.start_time:.2f}-{segment.end_time:.2f}" for segment in ordered)
            self.append_log(f"[SEGMENTS] Preview Shuffle Order: {order}")

        def save_timeline(self) -> None:
            path, _ = QFileDialog.getSaveFileName(self, "Save Timeline", "timeline_segments.json", "JSON (*.json)")
            if not path:
                return
            payload = {
                "video": str(self.current_video_path) if self.current_video_path else None,
                "segments": [segment.to_json() for segment in self._timeline_segments()],
            }
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.append_log(f"[SEGMENTS] Saved timeline: {path}")

        def load_timeline(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Load Timeline", "", "JSON (*.json)")
            if not path:
                return
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.state.scene_shuffle.manual_segments = [
                TimelineSegment.from_json(item, default_source="manual").normalized(self.video_duration)
                for item in payload.get("segments", [])
            ]
            self.state.scene_shuffle.segment_video_path = str(self.current_video_path) if self.current_video_path else payload.get("video")
            self.manual_cut_undo_stack.clear()
            self.manual_cut_redo_stack.clear()
            self.refresh_timeline()
            self.append_log(f"[SEGMENTS] Loaded {len(self.state.scene_shuffle.manual_segments)} manual segments: {path}")

        def update_preview(self, video_path: Path) -> None:
            if not video_path.exists():
                self.append_log(f"[WARNING] Không tìm thấy video preview: {video_path}")
                return
            self._last_preview_frame_key = None
            self.update_preview_frame(self.timeline.current_time if hasattr(self.timeline, "current_time") else 0.05, force=True)

        def update_preview_frame(self, time_seconds: float, force: bool = False) -> None:
            if self.current_video_path is None or not self.current_video_path.exists():
                return
            bucket = max(0, int(float(time_seconds) * self.preview_frame_fps))
            source_hash = hashlib.sha1(str(self.current_video_path).encode("utf-8")).hexdigest()
            frame_key = (source_hash, bucket)
            if not force and frame_key == self._last_preview_frame_key:
                return
            preview_path = self.preview_cache_dir / f"{source_hash}_{bucket:06d}.jpg"
            try:
                if not preview_path.exists():
                    self.preview_renderer.extract_frame_at(self.current_video_path, preview_path, bucket / self.preview_frame_fps)
                self.preview.set_preview_image(preview_path)
                self._last_preview_frame_key = frame_key
                self.update_watermark_preview()
            except Exception as exc:
                self.append_log(f"[WARNING] Không tạo được preview frame tại {time_seconds:.2f}s: {exc}")

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
            self.set_safe_area_options("TikTok", True, True)
            overlay_pipeline = mode in {WorkflowMode.PIPELINE_2, WorkflowMode.PIPELINE_3, WorkflowMode.PIPELINE_4}
            self.update_watermark_preview()
            self.state.overlays.text_enabled = overlay_pipeline and bool(self.state.overlays.text.text.strip())
            self.state.overlays.highlight_enabled = overlay_pipeline and self.workflow.highlight_enabled.isChecked() and bool(self.state.overlays.highlight.text.strip())
            self.state.overlays.sticker_enabled = overlay_pipeline and self.state.overlays.sticker.path is not None
            self.state.overlays.text.template = self.workflow.template.currentText()
            self.state.overlays.text.set_font_size(self.workflow.font_size.value())
            self.state.overlays.text.motion = MotionPreset.from_label(self.workflow.motion.currentText())
            self.state.overlays.text.motion_speed = self.workflow.text_motion_speed_ratio()
            self.state.overlays.text.motion_strength = self.workflow.motion_strength_ratio(self.workflow.text_motion_strength)
            self.update_highlight_preview()
            self.update_watermark_preview()
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
            self.append_log(f"[INFO] Bắt đầu render batch vào: {output_directory_for_videos(self.state.videos, self.state.export.output_dir).resolve()}")
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
            self.export_button.setText("Render Video")
            self.status.showMessage(f"Hoàn tất {len(paths)} video")
            self.append_log(f"[SUCCESS] Hoàn tất {len(paths)} video.")
            if self.state.export.auto_open_output:
                self.open_output_folder()

        def render_failed(self, message: str) -> None:
            self.export_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.export_button.setText("Render Video")
            self.status.showMessage("Render lỗi")
            self.append_log("[ERROR] " + message)
else:
    class MainWindow:  # type: ignore[no-redef]
        pass
