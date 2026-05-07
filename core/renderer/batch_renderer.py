"""Sequential batch renderer that keeps the UI responsive via callbacks."""
from __future__ import annotations

import subprocess
from collections.abc import Callable

from core.pipeline.manager import PipelineManager
from models.project_state import ProjectState
from utils.ffmpeg_helper import FFmpegNotFoundError, subprocess_startupinfo, validate_ffmpeg_pair
from utils.file_helper import safe_output_path

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


class BatchRenderer:
    def __init__(self, manager: PipelineManager | None = None) -> None:
        self.manager = manager or PipelineManager()

    def render(
        self,
        state: ProjectState,
        progress: ProgressCallback | None = None,
        log: LogCallback | None = None,
    ) -> list[str]:
        outputs: list[str] = []
        total = len(state.videos)
        if total == 0:
            self._log(log, "Không có video trong queue.")
            return outputs

        try:
            ffmpeg_path, ffprobe_path = validate_ffmpeg_pair()
        except FFmpegNotFoundError as exc:
            self._log(log, f"Lỗi cấu hình FFmpeg: {exc}")
            raise

        self._log(log, f"FFmpeg: {ffmpeg_path}")
        self._log(log, f"FFprobe: {ffprobe_path}")
        for index, video in enumerate(state.videos, start=1):
            output = safe_output_path(state.export.output_dir, video)
            message = f"Đang render {index}/{total}: {video.name}"
            if progress:
                progress(index, total, message)
            self._log(log, message)
            cmd = self.manager.build_command(video, output, state)
            self._log(log, "Lệnh FFmpeg: " + " ".join(f'"{part}"' if " " in part else part for part in cmd))
            self._run_command(cmd, log)
            outputs.append(str(output))
            self._log(log, f"Hoàn tất: {output}")
        self._log(log, "Render batch hoàn tất.")
        return outputs

    def _run_command(self, cmd: list[str], log: LogCallback | None) -> None:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=subprocess_startupinfo(),
        )
        assert process.stdout is not None
        for line in process.stdout:
            line = line.strip()
            if line:
                self._log(log, line)
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg render lỗi (exit code {return_code}). Xem log phía trên để biết chi tiết.")

    @staticmethod
    def _log(log: LogCallback | None, message: str) -> None:
        if log:
            log(message)
