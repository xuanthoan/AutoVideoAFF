"""FFmpeg overlay engine for Qt-rendered social typography assets."""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.overlays.motion_engine import MotionEngine
from core.overlays.template_manager import TemplateManager
from core.overlays.typography_engine import SocialTypographyRenderer
from models.text_overlay import TextOverlay


class TextEngine:
    def __init__(self) -> None:
        self.templates = TemplateManager()
        self.motion = MotionEngine()
        self.typography = SocialTypographyRenderer()

    def build_filter(
        self,
        video_label: str,
        text_label: str,
        overlay: TextOverlay,
        suffix: str = "",
    ) -> tuple[str, str]:
        out = f"text_v{suffix}"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.start_time, overlay.end_time)
        chain = f"[{video_label}][{text_label}]overlay=x={x}:y={y}:enable='{enable}'[{out}]"
        return chain, out

    def render_asset(
        self,
        overlay: TextOverlay,
        canvas_width: int,
        canvas_height: int,
        temp_files: list[Path] | None = None,
    ) -> Path:
        template = self.templates.get(overlay.template)
        handle = tempfile.NamedTemporaryFile(prefix="autovideoaff_text_", suffix=".png", delete=False)
        path = Path(handle.name)
        handle.close()
        self.typography.render_png(path, overlay.text, template, overlay.font_size, canvas_width, canvas_height)
        if temp_files is not None:
            temp_files.append(path)
        return path
