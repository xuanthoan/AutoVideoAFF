"""FFmpeg/FFprobe helpers."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def executable(name: str) -> str:
    bundled = Path("bin") / (name + (".exe" if not name.endswith(".exe") else ""))
    if bundled.exists():
        return str(bundled)
    return shutil.which(name) or name


def probe_duration(path: Path) -> float:
    cmd = [
        executable("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0
