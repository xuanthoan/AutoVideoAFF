"""Fast preview frame extraction."""
from __future__ import annotations

import subprocess
from pathlib import Path

from utils.ffmpeg_helper import executable, subprocess_startupinfo


class PreviewRenderer:
    def extract_first_valid_frame(self, input_path: Path, output_path: Path) -> Path:
        return self.extract_frame_at(input_path, output_path, 0.05)

    def extract_preview_sequence(self, input_path: Path, output_dir: Path, fps: int = 12, duration: float | None = None) -> list[Path]:
        """Extract a lightweight cached preview sequence once, not during every playback tick."""
        output_dir.mkdir(parents=True, exist_ok=True)
        pattern = output_dir / "frame_%06d.jpg"
        fps = max(1, int(fps))
        cmd = [executable("ffmpeg"), "-y", "-i", str(input_path)]
        if duration is not None:
            cmd.extend(["-t", f"{max(0.1, float(duration)):.3f}"])
        cmd.extend(["-vf", f"fps={fps},scale=720:-2", "-q:v", "4", str(pattern)])
        subprocess.run(cmd, check=True, capture_output=True, startupinfo=subprocess_startupinfo())
        return sorted(output_dir.glob("frame_*.jpg"))

    def extract_frame_at(self, input_path: Path, output_path: Path, time_seconds: float) -> Path:
        """Extract one preview frame near ``time_seconds`` for playback/scrubbing."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        seek = max(0.0, float(time_seconds))
        cmd = [executable("ffmpeg"), "-y", "-ss", f"{seek:.3f}", "-i", str(input_path), "-frames:v", "1", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True, startupinfo=subprocess_startupinfo())
        return output_path
