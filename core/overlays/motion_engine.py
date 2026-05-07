"""Motion expression builder.

Sticker and text motion always starts from the original texture label and emits a
single transformed overlay per frame, preventing recursive bounce/framebuffer bugs.
"""
from __future__ import annotations

from models.overlay import MotionPreset


class MotionEngine:
    def position_expr(self, x: float, y: float, motion: MotionPreset, duration: float) -> tuple[str, str, str]:
        base_x = f"(W-w)*{x:.4f}"
        base_y = f"(H-h)*{y:.4f}"
        enable = f"between(t,0,{duration:.3f})"
        if motion == MotionPreset.SLIDE:
            return f"{base_x}-w*(1-min(t/0.35\\,1))", base_y, enable
        if motion == MotionPreset.BOUNCE:
            return base_x, f"{base_y}+18*sin(18*t)*exp(-2*t)", enable
        if motion == MotionPreset.ELASTIC:
            return base_x, f"{base_y}+28*sin(22*t)*exp(-3*t)", enable
        return base_x, base_y, enable

    def alpha_expr(self, motion: MotionPreset) -> str:
        if motion == MotionPreset.FADE:
            return "if(lt(t,0.35),t/0.35,if(gt(t,2.65),max(0,(3-t)/0.35),1))"
        return "1"
