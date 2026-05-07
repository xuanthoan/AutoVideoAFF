"""Video queue panel."""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QFileDialog, QListWidget, QPushButton, QVBoxLayout, QWidget
except ImportError:
    Signal = QFileDialog = QListWidget = QPushButton = QVBoxLayout = QWidget = None

from utils.file_helper import collect_videos


if QWidget:
    class QueuePanel(QWidget):
        changed = Signal(list)

        def __init__(self) -> None:
            super().__init__()
            self.list = QListWidget()
            self.list.setDragDropMode(QListWidget.InternalMove)
            add_video = QPushButton("Add video")
            add_folder = QPushButton("Add folder")
            remove = QPushButton("Remove selected")
            clear = QPushButton("Clear all")
            add_video.clicked.connect(self.add_video)
            add_folder.clicked.connect(self.add_folder)
            remove.clicked.connect(lambda: [self.list.takeItem(i.row()) for i in self.list.selectedIndexes()])
            clear.clicked.connect(self.list.clear)
            layout = QVBoxLayout(self)
            for widget in (self.list, add_video, add_folder, remove, clear):
                layout.addWidget(widget)

        def paths(self) -> list[Path]:
            return [Path(self.list.item(i).text()) for i in range(self.list.count())]

        def add_video(self) -> None:
            files, _ = QFileDialog.getOpenFileNames(self, "Add videos", "", "Videos (*.mp4 *.mov *.mkv *.webm *.avi)")
            for file in files:
                self.list.addItem(file)
            self.changed.emit(self.paths())

        def add_folder(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "Add folder")
            if folder:
                for path in collect_videos(Path(folder)):
                    self.list.addItem(str(path))
            self.changed.emit(self.paths())
else:
    class QueuePanel:  # type: ignore[no-redef]
        pass
