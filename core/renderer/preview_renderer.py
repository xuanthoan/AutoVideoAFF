"""Fast preview frame extraction."""
from __future__ import annotations

import subprocess
from pathlib import Path

from utils.ffmpeg_helper import executable, subprocess_startupinfo


class PreviewRenderer:
    def extract_first_valid_frame(self, input_path: Path, output_path: Path) -> Path:
        return self.extract_frame_at(input_path, output_path, 0.05)

    def extract_frame_at(self, input_path: Path, output_path: Path, time_seconds: float) -> Path:
        """Extract one preview frame near ``time_seconds`` for playback/scrubbing."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        seek = max(0.0, float(time_seconds))
        cmd = [executable("ffmpeg"), "-y", "-ss", f"{seek:.3f}", "-i", str(input_path), "-frames:v", "1", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True, startupinfo=subprocess_startupinfo())
        return output_path
