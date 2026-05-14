"""Compact overlay-only timeline for social-video timing control."""
from __future__ import annotations

from dataclasses import dataclass

try:
    from PySide6.QtCore import QRectF, Qt, Signal
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
except ImportError:  # keep non-GUI imports lightweight in CI
    QRectF = Qt = Signal = QColor = QPainter = QPen = QHBoxLayout = QLabel = QListWidget = QListWidgetItem = QPushButton = QScrollArea = QSizePolicy = QVBoxLayout = QWidget = None


@dataclass(slots=True)
class TimelineOverlayItem:
    key: str
    kind: str
    label: str
    start: float
    end: float
    visible: bool = True

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(slots=True)
class SegmentTimelineItem:
    start: float
    end: float
    source: str = "auto"
    enabled: bool = True
    locked: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


if QWidget:
    class MiniTimelineTracks(QWidget):
        playheadChanged = Signal(float)
        overlayTimingChanged = Signal(str, float, float)
        overlaySelected = Signal(str)

        TRACK_HEIGHT = 26
        TRACK_GAP = 8
        LEFT_GUTTER = 74
        RIGHT_PAD = 8
        EDGE_HANDLE = 7
        SNAP_THRESHOLD = 5
        MIN_DURATION = 0.1

        def __init__(self) -> None:
            super().__init__()
            self.setMinimumHeight(188)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
            self.setMouseTracking(True)
            self.setStyleSheet("background:#151515;border:1px solid #303030;border-radius:6px;")
            self.items: list[TimelineOverlayItem] = []
            self.segments: list[SegmentTimelineItem] = []
            self.video_duration = 6.0
            self.zoom_factor = 1.0
            self.playhead_time = 0.0
            self.selected_key: str | None = None
            self._mode: str | None = None
            self._drag_key: str | None = None
            self._drag_offset = 0.0
            self._base_width = 900
            self._refresh_geometry()

        def set_items(self, items: list[TimelineOverlayItem]) -> None:
            self.items = items[:100]
            if self.selected_key not in {item.key for item in self.items}:
                self.selected_key = self.items[0].key if self.items else None
            self._refresh_geometry()

        def set_segments(self, segments: list[SegmentTimelineItem]) -> None:
            self.segments = segments[:200]
            self.update()

        def set_zoom(self, zoom_factor: float) -> None:
            self.zoom_factor = min(max(float(zoom_factor), 1.0), 8.0)
            self._refresh_geometry()

        def set_duration(self, duration: float) -> None:
            self.video_duration = max(0.1, float(duration))
            self.playhead_time = min(self.playhead_time, self.video_duration)
            self._refresh_geometry()

        def set_playhead(self, time_seconds: float) -> None:
            old_x = int(self._time_to_x(self.playhead_time))
            self.playhead_time = min(max(float(time_seconds), 0.0), self.video_duration)
            new_x = int(self._time_to_x(self.playhead_time))
            self.update(max(0, old_x - 3), 0, 7, self.height())
            self.update(max(0, new_x - 3), 0, 7, self.height())

        def select_overlay(self, key: str) -> None:
            self.selected_key = key
            self.update()

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            area = self._track_area_width()
            painter.setPen(QColor("#737373"))
            painter.drawText(8, 17, "SEGMENTS")
            self._draw_segments(painter)
            first_row = max(0, int((event.rect().top() - 25) // (self.TRACK_HEIGHT + self.TRACK_GAP)))
            last_row = min(len(self.items), int((event.rect().bottom() - 25) // (self.TRACK_HEIGHT + self.TRACK_GAP)) + 2)
            for idx in range(first_row, last_row):
                item = self.items[idx]
                y = self._row_y(idx)
                painter.setPen(QColor("#a8a8a8" if item.visible else "#666"))
                painter.drawText(8, int(y + 18), item.label)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor("#2a2a2a"), 1))
                painter.drawRoundedRect(QRectF(self.LEFT_GUTTER, y, area, self.TRACK_HEIGHT), 4, 4)
                rect = self._item_rect(item, idx)
                color = QColor("#f28c28") if item.kind == "text" else QColor("#2f8cff")
                color.setAlpha(225 if item.visible else 90)
                painter.setBrush(color)
                painter.setPen(QPen(QColor("#ffe3b6") if item.key == self.selected_key else QColor("#111"), 2))
                painter.drawRoundedRect(rect, 5, 5)
                painter.setPen(QColor("#101010"))
                painter.drawText(rect.adjusted(8, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, f"{item.duration:.2f}s")
            x = self._time_to_x(self.playhead_time)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(int(x), 0, int(x), self.height())

        def wheelEvent(self, event):
            if event.modifiers() & Qt.ControlModifier:
                step = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
                self.set_zoom(self.zoom_factor * step)
                return
            return super().wheelEvent(event)

        def _draw_segments(self, painter: QPainter) -> None:
            y = 4
            h = 16
            for segment in self.segments:
                start_x = self._time_to_x(segment.start)
                end_x = self._time_to_x(segment.end)
                rect = QRectF(start_x, y, max(4, end_x - start_x), h)
                color = QColor("#4cc46b" if segment.source == "auto" else "#d8a13c")
                color.setAlpha(210 if segment.enabled else 70)
                painter.setBrush(color)
                painter.setPen(QPen(QColor("#f6f6f6") if segment.locked else QColor("#202020"), 1))
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(QColor("#101010"))
                painter.drawText(rect.adjusted(4, 0, -2, 0), Qt.AlignVCenter | Qt.AlignLeft, segment.source.upper())

        def mousePressEvent(self, event):
            if event.button() != Qt.LeftButton:
                return super().mousePressEvent(event)
            pos = event.position()
            for idx, item in enumerate(self.items):
                rect = self._item_rect(item, idx)
                if rect.contains(pos):
                    self.selected_key = item.key
                    self._drag_key = item.key
                    self._drag_offset = self._x_to_time(pos.x()) - item.start
                    if abs(pos.x() - rect.left()) <= self.EDGE_HANDLE:
                        self._mode = "resize_left"
                    elif abs(pos.x() - rect.right()) <= self.EDGE_HANDLE:
                        self._mode = "resize_right"
                    else:
                        self._mode = "move"
                    self.overlaySelected.emit(item.key)
                    self.update()
                    return
            self.set_playhead(self._x_to_time(pos.x()))
            self.playheadChanged.emit(self.playhead_time)

        def mouseMoveEvent(self, event):
            pos = event.position()
            if not self._drag_key:
                if pos.x() >= self.LEFT_GUTTER:
                    self.setCursor(Qt.SplitHCursor)
                return super().mouseMoveEvent(event)
            item = next((candidate for candidate in self.items if candidate.key == self._drag_key), None)
            if item is None:
                return
            raw_time = self._x_to_time(pos.x())
            if self._mode == "move":
                duration = item.duration
                start = min(max(raw_time - self._drag_offset, 0.0), max(0.0, self.video_duration - duration))
                start = self._snapped_start(start, duration, item)
                item.start = start
                item.end = start + duration
            elif self._mode == "resize_left":
                time_value = self._snapped_time(raw_time, item)
                item.start = min(max(time_value, 0.0), item.end - self.MIN_DURATION)
            elif self._mode == "resize_right":
                time_value = self._snapped_time(raw_time, item)
                item.end = max(min(time_value, self.video_duration), item.start + self.MIN_DURATION)
            self.overlayTimingChanged.emit(item.key, item.start, item.end)
            self.update()

        def mouseReleaseEvent(self, event):
            self._mode = None
            self._drag_key = None
            self.unsetCursor()
            return super().mouseReleaseEvent(event)

        def _snapped_time(self, time_value: float, item: TimelineOverlayItem) -> float:
            snap_seconds = self._snap_seconds()
            for snap in self._snap_points(item):
                if abs(time_value - snap) <= snap_seconds:
                    return snap
            return time_value

        def _snapped_start(self, start: float, duration: float, item: TimelineOverlayItem) -> float:
            snap_seconds = self._snap_seconds()
            for snap in self._snap_points(item):
                if abs(start - snap) <= snap_seconds:
                    return min(max(snap, 0.0), max(0.0, self.video_duration - duration))
                if abs((start + duration) - snap) <= snap_seconds:
                    return min(max(snap - duration, 0.0), max(0.0, self.video_duration - duration))
            return start

        def _snap_points(self, item: TimelineOverlayItem) -> list[float]:
            points = [self.playhead_time]
            for other in self.items:
                if other.key != item.key:
                    points.extend([other.start, other.end])
            return points

        def _snap_seconds(self) -> float:
            pixels_per_second = self._track_area_width() / self.video_duration
            return self.SNAP_THRESHOLD / max(pixels_per_second, 1)

        def _row_y(self, index: int) -> float:
            return 25 + index * (self.TRACK_HEIGHT + self.TRACK_GAP)

        def _item_rect(self, item: TimelineOverlayItem, index: int) -> QRectF:
            start_x = self._time_to_x(item.start)
            end_x = self._time_to_x(item.end)
            return QRectF(start_x, self._row_y(index), max(8, end_x - start_x), self.TRACK_HEIGHT)

        def _refresh_geometry(self) -> None:
            rows_height = 32 + len(self.items) * (self.TRACK_HEIGHT + self.TRACK_GAP) + 10
            height = max(188, rows_height)
            width = max(self._base_width, int(self._base_width * self.zoom_factor))
            self.setMinimumSize(width, height)
            self.resize(width, height)
            self.updateGeometry()
            self.update()

        def _track_area_width(self) -> float:
            return max(1.0, self.width() - self.LEFT_GUTTER - self.RIGHT_PAD)

        def _time_to_x(self, time_seconds: float) -> float:
            return self.LEFT_GUTTER + (min(max(time_seconds, 0.0), self.video_duration) / self.video_duration) * self._track_area_width()

        def _x_to_time(self, x: float) -> float:
            normalized = (x - self.LEFT_GUTTER) / self._track_area_width()
            return min(max(normalized, 0.0), 1.0) * self.video_duration


    class MiniTimeline(QWidget):
        playheadChanged = Signal(float)
        overlayTimingChanged = Signal(str, float, float)
        overlaySelected = Signal(str)
        overlayVisibilityChanged = Signal(str, bool)
        generateAutoSegmentsRequested = Signal()
        addCutRequested = Signal(float)
        previewShuffleOrderRequested = Signal()
        saveTimelineRequested = Signal()
        loadTimelineRequested = Signal()
        segmentEnabledChanged = Signal(int, bool)
        segmentLockedChanged = Signal(int, bool)
        removeSegmentRequested = Signal(int)
        undoCutRequested = Signal()
        redoCutRequested = Signal()
        clearManualCutsRequested = Signal()
        playRequested = Signal()
        pauseRequested = Signal()
        stopRequested = Signal()

        def __init__(self) -> None:
            super().__init__()
            self.setMinimumHeight(280)
            self.setMaximumHeight(460)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setStyleSheet("QWidget{background:#101010;color:#dedede;} QPushButton{background:#252525;color:#eee;border:1px solid #3a3a3a;padding:3px 8px;border-radius:4px;} QListWidget{background:#171717;border:1px solid #303030;border-radius:5px;}")
            self.current_time = 0.0
            self.video_duration = 6.0
            self._is_playback_requested = False
            self.play_button = QPushButton("Play")
            self.pause_button = QPushButton("Pause")
            self.stop_button = QPushButton("Stop")
            self.generate_segments_button = QPushButton("Generate Auto Segments")
            self.add_cut_button = QPushButton("Add Cut")
            self.undo_cut_button = QPushButton("Undo Cut")
            self.redo_cut_button = QPushButton("Redo Cut")
            self.clear_manual_cuts_button = QPushButton("Clear Manual Cuts")
            self.preview_order_button = QPushButton("Preview Shuffle Order")
            self.save_timeline_button = QPushButton("Save Timeline")
            self.load_timeline_button = QPushButton("Load Timeline")
            self.time_label = QLabel("00:00.00 / 00:06.00")
            self.overlay_list = QListWidget()
            self.overlay_list.setMaximumWidth(120)
            self.segment_list = QListWidget()
            self.segment_list.setMinimumWidth(260)
            self.segment_list.setToolTip("# | Start | End | Duration | Lock | Enable | Type")
            self.tracks = MiniTimelineTracks()
            self.track_scroll = QScrollArea()
            self.track_scroll.setWidgetResizable(False)
            self.track_scroll.setWidget(self.tracks)
            self.track_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.track_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.track_scroll.setMinimumHeight(188)
            controls = QHBoxLayout()
            controls.setContentsMargins(0, 0, 0, 0)
            controls.setSpacing(4)
            controls.addWidget(self.play_button)
            controls.addWidget(self.pause_button)
            controls.addWidget(self.stop_button)
            controls.addWidget(self.generate_segments_button)
            controls.addWidget(self.add_cut_button)
            controls.addWidget(self.undo_cut_button)
            controls.addWidget(self.redo_cut_button)
            controls.addWidget(self.clear_manual_cuts_button)
            controls.addWidget(self.preview_order_button)
            controls.addWidget(self.save_timeline_button)
            controls.addWidget(self.load_timeline_button)
            controls.addWidget(self.time_label)
            controls.addStretch()
            left = QVBoxLayout()
            left.setContentsMargins(0, 0, 0, 0)
            left.setSpacing(4)
            left.addLayout(controls)
            left.addWidget(self.track_scroll, 1)
            layout = QHBoxLayout(self)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(6)
            layout.addLayout(left, 1)
            layout.addWidget(self.segment_list, 0)
            layout.addWidget(self.overlay_list, 0)
            self.play_button.clicked.connect(self.play)
            self.pause_button.clicked.connect(self.pause)
            self.stop_button.clicked.connect(self.stop)
            self.generate_segments_button.clicked.connect(self.generateAutoSegmentsRequested.emit)
            self.add_cut_button.clicked.connect(lambda: self.addCutRequested.emit(self.current_time))
            self.undo_cut_button.clicked.connect(self.undoCutRequested.emit)
            self.redo_cut_button.clicked.connect(self.redoCutRequested.emit)
            self.clear_manual_cuts_button.clicked.connect(self.clearManualCutsRequested.emit)
            self.preview_order_button.clicked.connect(self.previewShuffleOrderRequested.emit)
            self.save_timeline_button.clicked.connect(self.saveTimelineRequested.emit)
            self.load_timeline_button.clicked.connect(self.loadTimelineRequested.emit)
            self.tracks.playheadChanged.connect(self.set_playhead_time)
            self.tracks.playheadChanged.connect(self.playheadChanged.emit)
            self.tracks.overlayTimingChanged.connect(self.overlayTimingChanged.emit)
            self.tracks.overlaySelected.connect(self._select_from_tracks)
            self.overlay_list.currentRowChanged.connect(self._select_from_list)
            self.overlay_list.itemChanged.connect(self._visibility_from_list)
            self.segment_list.itemChanged.connect(self._segment_flags_from_list)
            self.segment_list.itemDoubleClicked.connect(self._toggle_segment_lock)

        def set_segments(self, segments: list[SegmentTimelineItem]) -> None:
            self.segment_list.blockSignals(True)
            self.segment_list.clear()
            for index, segment in enumerate(segments, start=1):
                row_item = QListWidgetItem(self._segment_label(index, segment))
                row_item.setFlags(row_item.flags() | Qt.ItemIsUserCheckable)
                row_item.setCheckState(Qt.Checked if segment.enabled else Qt.Unchecked)
                self.segment_list.addItem(row_item)
            self.segment_list.blockSignals(False)
            self.tracks.set_segments(segments)

        def set_items(self, items: list[TimelineOverlayItem]) -> None:
            self.overlay_list.blockSignals(True)
            self.overlay_list.clear()
            for item in items[:100]:
                row_item = QListWidgetItem(item.label)
                row_item.setFlags(row_item.flags() | Qt.ItemIsUserCheckable)
                row_item.setCheckState(Qt.Checked if item.visible else Qt.Unchecked)
                self.overlay_list.addItem(row_item)
            self.overlay_list.blockSignals(False)
            self.tracks.set_items(items)
            if self.tracks.selected_key and self.overlay_list.currentRow() < 0:
                self.overlay_list.blockSignals(True)
                self.overlay_list.setCurrentRow(0)
                self.overlay_list.blockSignals(False)

        def set_duration(self, duration: float) -> None:
            self.video_duration = max(0.1, float(duration))
            self.tracks.set_duration(self.video_duration)
            self.set_playhead_time(min(self.current_time, self.video_duration))

        def set_playhead_time(self, time_seconds: float) -> None:
            self.current_time = min(max(float(time_seconds), 0.0), self.video_duration)
            self.tracks.set_playhead(self.current_time)
            self.time_label.setText(f"{self._format_time(self.current_time)} / {self._format_time(self.video_duration)}")

        def set_playback_active(self, active: bool) -> None:
            self._is_playback_requested = bool(active)

        def play(self) -> None:
            self.playRequested.emit()

        def pause(self) -> None:
            self._is_playback_requested = False
            self.pauseRequested.emit()

        def stop(self) -> None:
            self._is_playback_requested = False
            self.set_playhead_time(0.0)
            self.playheadChanged.emit(0.0)
            self.stopRequested.emit()

        def _select_from_tracks(self, key: str) -> None:
            for row, item in enumerate(self.tracks.items):
                if item.key == key:
                    self.overlay_list.blockSignals(True)
                    self.overlay_list.setCurrentRow(row)
                    self.overlay_list.blockSignals(False)
                    break
            self.overlaySelected.emit(key)

        def _select_from_list(self, row: int) -> None:
            if 0 <= row < len(self.tracks.items):
                key = self.tracks.items[row].key
                self.tracks.select_overlay(key)
                self.overlaySelected.emit(key)

        def _visibility_from_list(self, item: QListWidgetItem) -> None:
            row = self.overlay_list.row(item)
            if 0 <= row < len(self.tracks.items):
                timeline_item = self.tracks.items[row]
                timeline_item.visible = item.checkState() == Qt.Checked
                self.tracks.update()
                self.overlayVisibilityChanged.emit(timeline_item.key, timeline_item.visible)

        def _segment_flags_from_list(self, item: QListWidgetItem) -> None:
            row = self.segment_list.row(item)
            if 0 <= row < len(self.tracks.segments):
                enabled = item.checkState() == Qt.Checked
                self.tracks.segments[row].enabled = enabled
                self.tracks.update()
                self.segmentEnabledChanged.emit(row, enabled)

        def _toggle_segment_lock(self, item: QListWidgetItem) -> None:
            row = self.segment_list.row(item)
            if 0 <= row < len(self.tracks.segments):
                locked = not self.tracks.segments[row].locked
                self.tracks.segments[row].locked = locked
                item.setText(self._segment_label(row + 1, self.tracks.segments[row]))
                self.tracks.update()
                self.segmentLockedChanged.emit(row, locked)

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Space:
                self.pause() if self._is_playback_requested else self.play()
                return
            if event.key() == Qt.Key_Left:
                self.set_playhead_time(max(0.0, self.current_time - 1 / 30))
                self.playheadChanged.emit(self.current_time)
                return
            if event.key() == Qt.Key_Right:
                self.set_playhead_time(min(self.video_duration, self.current_time + 1 / 30))
                self.playheadChanged.emit(self.current_time)
                return
            if event.key() == Qt.Key_C:
                self.addCutRequested.emit(self.current_time)
                return
            if event.key() == Qt.Key_Delete:
                row = self.segment_list.currentRow()
                if row >= 0:
                    self.removeSegmentRequested.emit(row)
                return
            return super().keyPressEvent(event)

        @staticmethod
        def _segment_label(index: int, segment: SegmentTimelineItem) -> str:
            lock = "🔒" if segment.locked else "☐"
            enabled = "☑" if segment.enabled else "☐"
            return f"{index} | {segment.start:.2f} | {segment.end:.2f} | {segment.duration:.2f} | {lock} | {enabled} | {segment.source.upper()}"

        @staticmethod
        def _format_time(seconds: float) -> str:
            minutes = int(seconds // 60)
            remainder = seconds - minutes * 60
            return f"{minutes:02d}:{remainder:05.2f}"
else:
    class MiniTimeline:  # type: ignore[no-redef]
        pass

