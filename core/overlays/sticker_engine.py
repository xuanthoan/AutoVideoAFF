"""Sticker overlay filter builder."""
from __future__ import annotations

from core.overlays.motion_engine import MotionEngine
from models.overlay import MotionPreset
from models.sticker_overlay import StickerOverlay


class StickerEngine:
    def __init__(self) -> None:
        self.motion = MotionEngine()

    def build_filter(self, video_label: str, sticker_label: str, overlay: StickerOverlay) -> tuple[str, str]:
        out = "sticker_v"
        prepared = "sticker_src"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.duration)
        width_expr, height_expr = self.motion.sticker_scale_expr(overlay.scale, overlay.motion)
        fade_filter = self._fade_filter(overlay.motion, overlay.duration)
        chain = (
            f"[{sticker_label}]scale=w='{width_expr}':h='{height_expr}':eval=frame,"
            f"rotate={overlay.rotation:.4f}*PI/180:ow=rotw(iw):oh=roth(ih):c=none,format=rgba"
            f"{fade_filter}[{prepared}];"
            f"[{video_label}][{prepared}]overlay=x={x}:y={y}:enable='{enable}'[{out}]"
        )
        return chain, out

    @staticmethod
    def _fade_filter(motion: MotionPreset, duration: float) -> str:
        if motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return ",fade=t=in:st=0:d=0.35:alpha=1"
        if motion == MotionPreset.FADE_OUT:
            return f",fade=t=out:st={max(duration - 0.35, 0):.3f}:d=0.35:alpha=1"
        return ""
