"""FFmpeg drawtext engine with multiline background support."""
from __future__ import annotations

from shlex import quote

from core.overlays.motion_engine import MotionEngine
from core.overlays.template_manager import TemplateManager
from models.text_overlay import TextOverlay


class TextEngine:
    def __init__(self) -> None:
        self.templates = TemplateManager()
        self.motion = MotionEngine()

    def build_filter(self, video_label: str, overlay: TextOverlay) -> tuple[str, str]:
        template = self.templates.get(overlay.template)
        out = "text_v"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.duration)
        text = overlay.text.replace("'", "\\'").replace(":", "\\:")
        line_h = f"{overlay.font_size + 12}"
        boxborder = template.padding
        drawtext = (
            f"[{video_label}]drawtext=text='{text}':fontsize={overlay.font_size}:fontcolor={template.font_color}:"
            f"borderw={template.stroke_width}:bordercolor={template.border_color}:shadowcolor={template.shadow_color}:"
            f"shadowx=3:shadowy=3:line_spacing=12:box=1:boxcolor={template.box_color}:boxborderw={boxborder}:"
            f"x={x}:y={y}+(max_glyph_a-text_h)/10:enable='{enable}'[{out}]"
        )
        return drawtext, out
