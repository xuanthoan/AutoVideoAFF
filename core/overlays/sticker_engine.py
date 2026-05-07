"""Sticker overlay filter builder."""
from __future__ import annotations

from core.overlays.motion_engine import MotionEngine
from models.sticker_overlay import StickerOverlay


class StickerEngine:
    def __init__(self) -> None:
        self.motion = MotionEngine()

    def build_filter(self, video_label: str, sticker_label: str, overlay) -> tuple[str, str]:
        out = "sticker_v"
        prepared = "sticker_src"
        x, y, enable = self.motion.position_expr(overlay.x, overlay.y, overlay.motion, overlay.duration)
        chain = (
            f"[{sticker_label}]scale=iw*{overlay.scale:.4f}:ih*{overlay.scale:.4f},"
            f"rotate={overlay.rotation:.4f}*PI/180:ow=rotw(iw):oh=roth(ih):c=none[{prepared}];"
            f"[{video_label}][{prepared}]overlay=x={x}:y={y}:enable='{enable}'[{out}]"
        )
        return chain, out
