"""Sequential batch renderer that keeps the UI responsive via callbacks."""
from __future__ import annotations

import subprocess
from collections.abc import Callable

from core.pipeline.manager import PipelineManager
from models.project_state import ProjectState
from utils.file_helper import safe_output_path

ProgressCallback = Callable[[int, int, str], None]


class BatchRenderer:
    def __init__(self, manager: PipelineManager | None = None) -> None:
        self.manager = manager or PipelineManager()

    def render(self, state: ProjectState, progress: ProgressCallback | None = None) -> list[str]:
        outputs: list[str] = []
        total = len(state.videos)
        for index, video in enumerate(state.videos, start=1):
            output = safe_output_path(state.export.output_dir, video)
            if progress:
                progress(index, total, f"Đang render {index}/{total}")
            cmd = self.manager.build_command(video, output, state)
            subprocess.run(cmd, check=True)
            outputs.append(str(output))
        return outputs
