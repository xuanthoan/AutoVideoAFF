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
        if motion == MotionPreset.SLIDE_UP:
            return base_x, f"{base_y}+h*(1-min(t/0.35\\,1))", enable
        if motion == MotionPreset.SLIDE_DOWN:
            return base_x, f"{base_y}-h*(1-min(t/0.35\\,1))", enable
        if motion == MotionPreset.BOUNCE:
            return base_x, f"{base_y}+18*sin(18*t)*exp(-2*t)", enable
        if motion == MotionPreset.DRIFT:
            return f"{base_x}+18*sin(t*0.8)", f"{base_y}+10*cos(t*0.6)", enable
        if motion == MotionPreset.ELASTIC:
            return base_x, f"{base_y}+28*sin(22*t)*exp(-3*t)", enable
        return base_x, base_y, enable

    def alpha_expr(self, motion: MotionPreset, duration: float) -> str:
        if motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return "if(lt(t,0.35),t/0.35,1)"
        if motion == MotionPreset.FADE_OUT:
            return f"if(gt(t,{max(duration - 0.35, 0):.3f}),max(0,({duration:.3f}-t)/0.35),1)"
        return "1"

    def sticker_scale_expr(self, scale: float, motion: MotionPreset) -> tuple[str, str]:
        base_w = f"iw*{scale:.4f}"
        base_h = f"ih*{scale:.4f}"
        if motion in {MotionPreset.POP, MotionPreset.ZOOM, MotionPreset.SCALE}:
            pop = "(0.65+0.35*min(t/0.25\\,1)+0.08*sin(24*t)*exp(-6*t))"
            return f"{base_w}*{pop}", f"{base_h}*{pop}"
        return base_w, base_h
