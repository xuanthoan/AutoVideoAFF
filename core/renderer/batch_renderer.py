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
    def __init__(self, manager: PipelineManager | None = None, debug: bool = False) -> None:
        self.manager = manager or PipelineManager()
        self.debug = debug

    def render(
        self,
        state: ProjectState,
        progress: ProgressCallback | None = None,
        log: LogCallback | None = None,
    ) -> list[str]:
        outputs: list[str] = []
        total = len(state.videos)
        if total == 0:
            self._log(log, "WARNING", "Không có video trong queue.")
            return outputs

        try:
            validate_ffmpeg_pair()
        except FFmpegNotFoundError as exc:
            self._log(log, "ERROR", str(exc))
            raise

        self._log(log, "INFO", "FFmpeg đã sẵn sàng.")
        for index, video in enumerate(state.videos, start=1):
            output = safe_output_path(state.export.output_dir, video)
            temp_output = temporary_output_path(output)
            temp_audio = temporary_output_path(output.with_suffix(".m4a"))
            temp_output.unlink(missing_ok=True)
            temp_audio.unlink(missing_ok=True)
            message = f"Đang render {index}/{total}: {video.name}"
            if progress:
                progress(index, total, message)
            self._log(log, "INFO", message)
            self._log(log, "INFO", f"Output: {output}")

            original_audio_path: Path | None = None
            try:
                if state.scene_shuffle.enabled:
                    self._log(log, "INFO", "Tách audio gốc trước khi shuffle.")
                    original_audio_path = self._extract_original_audio(video, temp_audio, log)
                    self._log(log, "INFO", "Detecting scenes...")
                    self._log(log, "INFO", "Splitting video-only segments...")
                    self._log(log, "INFO", "Shuffling video segments only...")
                if state.image_composite.enabled:
                    self._log(log, "INFO", "Applying image composite...")
                if state.overlays.enabled:
                    self._log(log, "INFO", "Rendering overlays...")
                self._log(log, "INFO", "Exporting final video...")
                cmd = self.manager.build_command(video, temp_output, state, original_audio_path=original_audio_path)
                if self.debug:
                    self._log(log, "INFO", "Lệnh FFmpeg: " + self._format_command(cmd))
                self._run_command(cmd, log)
                self._verify_output(temp_output, log)
                temp_output.replace(output)
                self._verify_output(output, log, quiet=True)
                outputs.append(str(output))
                self._log(log, "SUCCESS", f"Video complete: {output}")
            finally:
                temp_audio.unlink(missing_ok=True)
        self._log(log, "SUCCESS", "Render batch hoàn tất.")
        return outputs

    def _extract_original_audio(self, video: Path, audio_output: Path, log: LogCallback | None) -> Path | None:
        copy_cmd = [executable("ffmpeg"), "-y", "-i", str(video), "-vn", "-acodec", "copy", str(audio_output)]
        result = self._run_capture(copy_cmd)
        if result.returncode == 0 and audio_output.exists() and audio_output.stat().st_size > 0:
            return audio_output

        self._log(log, "WARNING", "Không copy được audio gốc, thử fallback AAC.")
        fallback_cmd = [executable("ffmpeg"), "-y", "-i", str(video), "-vn", "-c:a", "aac", str(audio_output)]
        result = self._run_capture(fallback_cmd)
        if result.returncode == 0 and audio_output.exists() and audio_output.stat().st_size > 0:
            return audio_output

        detail = self._stderr_tail(result)
        if "does not contain any stream" in detail or "matches no streams" in detail or "Stream map" in detail:
            self._log(log, "WARNING", "Video không có audio, xuất video không kèm audio.")
            return None
        raise RuntimeError(f"Không tách được audio gốc. {detail}")

    def _run_command(self, cmd: list[str], log: LogCallback | None) -> None:
        result = self._run_capture(cmd)
        if result.returncode != 0:
            detail = self._stderr_tail(result)
            self._log(log, "ERROR", detail)
            raise RuntimeError(f"FFmpeg render lỗi (exit code {result.returncode}).")
        if self.debug and result.stderr:
            self._log(log, "INFO", self._stderr_tail(result))

    def _run_capture(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=subprocess_startupinfo(),
        )

    def _verify_output(self, output: Path, log: LogCallback | None, quiet: bool = False) -> None:
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
        result = self._run_capture(cmd)
        if result.returncode != 0 or "video" not in result.stdout:
            detail = (result.stderr or result.stdout or "ffprobe không đọc được file").strip()
            raise RuntimeError(f"File output không hợp lệ hoặc không phát được: {output}. {detail}")
        if not quiet:
            self._log(log, "INFO", f"Đã xác minh output ({size / 1024 / 1024:.2f} MB).")

    @staticmethod
    def _stderr_tail(result: subprocess.CompletedProcess[str], lines: int = 12) -> str:
        output = result.stderr or result.stdout or "Không có log chi tiết từ FFmpeg."
        return "\n".join(output.strip().splitlines()[-lines:])

    @staticmethod
    def _format_command(cmd: list[str]) -> str:
        return " ".join(f'"{part}"' if " " in part else part for part in cmd)

    @staticmethod
    def _log(log: LogCallback | None, level: str, message: str) -> None:
        if log:
            log(f"[{level}] {message}")
