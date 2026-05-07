"""Fast preview frame extraction."""
from __future__ import annotations

import subprocess
from pathlib import Path

from utils.ffmpeg_helper import executable


class PreviewRenderer:
    def extract_first_valid_frame(self, input_path: Path, output_path: Path) -> Path:
        cmd = [executable("ffmpeg"), "-y", "-ss", "0.05", "-i", str(input_path), "-frames:v", "1", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
