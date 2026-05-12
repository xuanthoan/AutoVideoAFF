"""FFmpeg overlay engine for Qt-rendered social typography assets."""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.normalized_layout import NormalizedLayoutEngine
from core.overlays.motion_engine import MotionEngine
from core.overlays.template_manager import TemplateManager
from core.overlays.typography_engine import SocialTypographyRenderer
from models.text_overlay import TextOverlay


class TextEngine:
    def __init__(self, templates=None, prefix: str = "text") -> None:
        self.templates = templates or TemplateManager()
        self.prefix = prefix
        self.motion = MotionEngine()
        self.typography = SocialTypographyRenderer()
        self.layout = NormalizedLayoutEngine()
        self._asset_cache: dict[tuple[str, str, float, int, int], Path] = {}

    def build_filter(
        self,
        video_label: str,
        text_label: str,
        overlay: TextOverlay,
        suffix: str = "",
    ) -> tuple[str, str]:
        out = f"{self.prefix}_v{suffix}"
        prepared = f"{self.prefix}_src{suffix}"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.start_time, overlay.end_time, overlay.motion_speed, overlay.motion_strength)
        width_expr, height_expr = self.motion.region_scale_expr("iw", overlay.motion, overlay.start_time, overlay.end_time, speed=overlay.motion_speed, strength=overlay.motion_strength)
        alpha_filter = self.motion.alpha_filter(overlay.motion, overlay.start_time, overlay.end_time, speed=overlay.motion_speed, strength=overlay.motion_strength)
        chain = (
            f"[{text_label}]scale=w='{width_expr}':h='{height_expr}':eval=frame{alpha_filter}[{prepared}];"
            f"[{video_label}][{prepared}]overlay=x={x}:y={y}:eval=frame:enable='{enable}'[{out}]"
        )
        return chain, out

    def render_asset(
        self,
        overlay: TextOverlay,
        canvas_width: int,
        canvas_height: int,
        temp_files: list[Path] | None = None,
    ) -> Path:
        template_name = getattr(overlay, "template", getattr(overlay, "style", ""))
        template = self.templates.get(template_name)
        font_ratio = overlay.effective_font_ratio()
        key = (overlay.text, template_name, round(font_ratio, 6), canvas_width, canvas_height)
        path = self._asset_cache.get(key)
        if path is None or not path.exists():
            path = self._new_asset_path()
            self.typography.render_png(path, overlay.text, template, font_ratio, canvas_width, canvas_height)
            self._asset_cache[key] = path
        if temp_files is not None and path not in temp_files:
            temp_files.append(path)
        return path

    @staticmethod
    def _new_asset_path() -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="autovideoaff_text_region_", suffix=".png", delete=False)
        path = Path(handle.name)
        handle.close()
        return path
