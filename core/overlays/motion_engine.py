"""Motion expression builder.

Sticker and text motion always starts from the original texture label and emits a
single transformed overlay per frame, preventing recursive bounce/framebuffer bugs.
"""
from __future__ import annotations

from models.overlay import MotionPreset


class MotionEngine:
    def position_expr(self, x: float, y: float, motion: MotionPreset, start: float, end: float) -> tuple[str, str, str]:
        base_x = f"W*{x:.4f}-w/2"
        base_y = f"H*{y:.4f}-h/2"
        start = max(0.0, float(start))
        end = max(start + 0.1, float(end))
        enable = f"between(t,{start:.3f},{end:.3f})"
        local_t = f"(t-{start:.3f})"
        if motion == MotionPreset.SLIDE:
            return f"{base_x}-w*(1-min({local_t}/0.35\\,1))", base_y, enable
        if motion == MotionPreset.SLIDE_UP:
            return base_x, f"{base_y}+h*(1-min({local_t}/0.35\\,1))", enable
        if motion == MotionPreset.SLIDE_DOWN:
            return base_x, f"{base_y}-h*(1-min({local_t}/0.35\\,1))", enable
        if motion == MotionPreset.BOUNCE:
            return base_x, f"{base_y}+18*sin(18*{local_t})*exp(-2*{local_t})", enable
        if motion == MotionPreset.DRIFT:
            return f"{base_x}+18*sin({local_t}*0.8)", f"{base_y}+10*cos({local_t}*0.6)", enable
        if motion == MotionPreset.ELASTIC:
            return base_x, f"{base_y}+28*sin(22*{local_t})*exp(-3*{local_t})", enable
        return base_x, base_y, enable


    @staticmethod
    def local_time(start: float = 0.0) -> str:
        return f"(t-{max(0.0, float(start)):.3f})"

    def alpha_filter(self, motion: MotionPreset, start: float = 0.0, end: float | None = None, duration: float = 0.35) -> str:
        start = max(0.0, float(start))
        duration = max(float(duration), 0.05)
        if motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return f",format=rgba,fade=t=in:st={start:.3f}:d={duration:.3f}:alpha=1"
        if motion == MotionPreset.FADE_OUT:
            end_time = max(start, float(end)) if end is not None else start + duration
            fade_start = max(start, end_time - duration)
            return f",format=rgba,fade=t=out:st={fade_start:.3f}:d={duration:.3f}:alpha=1"
        return ",format=rgba"

    def region_scale_expr(self, base_width: str, motion: MotionPreset, start: float = 0.0) -> tuple[str, str]:
        local_t = self.local_time(start)
        if motion in {MotionPreset.POP, MotionPreset.ZOOM}:
            pop = f"if(lt({local_t},0),0.85,if(lt({local_t},0.18),0.85+0.27*({local_t}/0.18),if(lt({local_t},0.35),1.12-0.12*(({local_t}-0.18)/0.17),1)))"
            return f"{base_width}*{pop}", "-1"
        if motion in {MotionPreset.BOUNCE, MotionPreset.SCALE}:
            bounce = f"if(lt({local_t},0),0.85,if(lt({local_t},0.25),0.85+0.23*({local_t}/0.25),if(lt({local_t},0.55),1.08-0.08*(({local_t}-0.25)/0.30),1)))"
            return f"{base_width}*{bounce}", "-1"
        return base_width, "-1"


    def preview_alpha(
        self,
        motion: MotionPreset | str,
        local_t: float,
        overlay_duration: float | None = None,
        fade_duration: float = 0.35,
    ) -> float:
        preset = MotionPreset.from_label(str(motion)) if not isinstance(motion, MotionPreset) else motion
        fade_duration = max(fade_duration, 0.05)
        if preset in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return min(max(local_t / fade_duration, 0.0), 1.0)
        if preset == MotionPreset.FADE_OUT:
            duration = max(float(overlay_duration), fade_duration) if overlay_duration is not None else fade_duration
            fade_t = local_t - max(duration - fade_duration, 0.0)
            return 1.0 - min(max(fade_t / fade_duration, 0.0), 1.0)
        return 1.0

    def preview_scale(self, motion: MotionPreset | str, local_t: float) -> float:
        preset = MotionPreset.from_label(str(motion)) if not isinstance(motion, MotionPreset) else motion
        if preset in {MotionPreset.POP, MotionPreset.ZOOM}:
            if local_t < 0:
                return 0.85
            if local_t < 0.18:
                return 0.85 + 0.27 * (local_t / 0.18)
            if local_t < 0.35:
                return 1.12 - 0.12 * ((local_t - 0.18) / 0.17)
            return 1.0
        if preset in {MotionPreset.BOUNCE, MotionPreset.SCALE}:
            if local_t < 0:
                return 0.85
            if local_t < 0.25:
                return 0.85 + 0.23 * (local_t / 0.25)
            if local_t < 0.55:
                return 1.08 - 0.08 * ((local_t - 0.25) / 0.30)
            return 1.0
        return 1.0

    def alpha_expr(self, motion: MotionPreset, duration: float) -> str:
        if motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return "if(lt(t,0.35),t/0.35,1)"
        if motion == MotionPreset.FADE_OUT:
            return f"if(gt(t,{max(duration - 0.35, 0):.3f}),max(0,({duration:.3f}-t)/0.35),1)"
        return "1"

    def sticker_scale_expr(self, scale_ratio: float, motion: MotionPreset, canvas_width: int, start: float = 0.0) -> tuple[str, str]:
        target_w = max(1, round(canvas_width * min(max(scale_ratio, 0.01), 1.0)))
        base_w = str(target_w)
        return self.region_scale_expr(base_w, motion, start)
