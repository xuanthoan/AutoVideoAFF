"""Sequential batch renderer that keeps the UI responsive via callbacks."""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from core.pipeline.manager import PipelineManager
from models.project_state import ProjectState
from utils.ffmpeg_helper import FFmpegNotFoundError, executable, subprocess_startupinfo, validate_ffmpeg_pair
from utils.file_helper import safe_output_path, temporary_output_path

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
            temp_output = temporary_output_path(output)
            temp_output.unlink(missing_ok=True)
            message = f"Đang render {index}/{total}: {video.name}"
            if progress:
                progress(index, total, message)
            self._log(log, message)
            self._log(log, f"Output tạm: {temp_output}")
            self._log(log, f"Output cuối: {output}")
            cmd = self.manager.build_command(video, temp_output, state)
            self._log(log, "Lệnh FFmpeg: " + self._format_command(cmd))
            self._run_command(cmd, log)
            self._verify_output(temp_output, log)
            temp_output.replace(output)
            self._verify_output(output, log)
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

    def _verify_output(self, output: Path, log: LogCallback | None) -> None:
        if not output.exists():
            raise FileNotFoundError(f"Không tìm thấy file output sau render: {output}")
        size = output.stat().st_size
        if size <= 0:
            raise RuntimeError(f"File output rỗng: {output}")
        cmd = [
            executable("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=subprocess_startupinfo())
        if result.returncode != 0 or "video" not in result.stdout:
            detail = (result.stderr or result.stdout or "ffprobe không đọc được file").strip()
            raise RuntimeError(f"File output không hợp lệ hoặc không phát được: {output}. {detail}")
        self._log(log, f"Đã xác minh output: {output} ({size / 1024 / 1024:.2f} MB)")

    @staticmethod
    def _format_command(cmd: list[str]) -> str:
        return " ".join(f'"{part}"' if " " in part else part for part in cmd)

    @staticmethod
    def _log(log: LogCallback | None, message: str) -> None:
        if log:
            log(message)
