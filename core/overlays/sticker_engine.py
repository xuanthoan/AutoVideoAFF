"""Sticker overlay filter builder."""
from __future__ import annotations

from core.overlays.motion_engine import MotionEngine
from models.overlay import MotionPreset
from models.sticker_overlay import StickerOverlay


class StickerEngine:
    def __init__(self) -> None:
        self.motion = MotionEngine()

    def build_filter(self, video_label: str, sticker_label: str, overlay: StickerOverlay, suffix: str = "") -> tuple[str, str]:
        out = f"sticker_v{suffix}"
        prepared = f"sticker_src{suffix}"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.start_time, overlay.end_time)
        width_expr, height_expr = self.motion.sticker_scale_expr(overlay.scale, overlay.motion)
        fade_filter = self._fade_filter(overlay)
        chain = (
            f"[{sticker_label}]scale=w='{width_expr}':h='{height_expr}':eval=frame,"
            f"rotate={overlay.rotation:.4f}*PI/180:ow=rotw(iw):oh=roth(ih):c=none,format=rgba"
            f"{fade_filter}[{prepared}];"
            f"[{video_label}][{prepared}]overlay=x={x}:y={y}:enable='{enable}'[{out}]"
        )
        return chain, out

    @staticmethod
    def _fade_filter(overlay: StickerOverlay) -> str:
        if overlay.motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return f",fade=t=in:st={overlay.start_time:.3f}:d=0.35:alpha=1"
        if overlay.motion == MotionPreset.FADE_OUT:
            return f",fade=t=out:st={max(overlay.end_time - 0.35, overlay.start_time):.3f}:d=0.35:alpha=1"
        return ""
