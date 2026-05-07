"""File-system helpers."""
from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def safe_output_path(output_dir: Path, source: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / f"{source.stem}.mp4"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"{source.stem}_{index:03d}.mp4"
        index += 1
    return candidate


def collect_videos(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.suffix.lower() in VIDEO_EXTENSIONS)
