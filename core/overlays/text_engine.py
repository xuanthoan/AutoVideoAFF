"""FFmpeg drawtext engine with multiline textfile support."""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.overlays.motion_engine import MotionEngine
from core.overlays.template_manager import TemplateManager
from models.text_overlay import TextOverlay


class TextEngine:
    def __init__(self) -> None:
        self.templates = TemplateManager()
        self.motion = MotionEngine()

    def build_filter(
        self,
        video_label: str,
        overlay: TextOverlay,
        suffix: str = "",
        temp_files: list[Path] | None = None,
    ) -> tuple[str, str]:
        template = self.templates.get(overlay.template)
        out = f"text_v{suffix}"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.start_time, overlay.end_time)
        text_file = self._write_text_file(overlay.text)
        if temp_files is not None:
            temp_files.append(text_file)
        boxborder = template.padding
        drawtext = (
            f"[{video_label}]drawtext=textfile='{self._escape_filter_path(text_file)}':"
            f"fontsize={overlay.font_size}:fontcolor={template.font_color}:"
            f"borderw={template.stroke_width}:bordercolor={template.border_color}:shadowcolor={template.shadow_color}:"
            f"shadowx=3:shadowy=3:line_spacing=12:box=1:boxcolor={template.box_color}:boxborderw={boxborder}:"
            f"x={x}:y={y}+(max_glyph_a-text_h)/10:enable='{enable}'[{out}]"
        )
        return drawtext, out

    @staticmethod
    def _write_text_file(text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            prefix="autovideoaff_text_",
            suffix=".txt",
            delete=False,
        )
        with handle:
            handle.write(text)
        return Path(handle.name)

    @staticmethod
    def _escape_filter_path(path: Path) -> str:
        return path.resolve().as_posix().replace("'", "\\'").replace(":", "\\:")
