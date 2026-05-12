"""Shared overlay motion evaluators for preview and FFmpeg export.

The renderer uses region-only RGBA overlay assets. This module is the single
source of truth for how those regions animate in both live preview and final
FFmpeg filtergraphs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import cos, pi, sin

from core.normalized_layout import NormalizedLayoutEngine, REFERENCE_HEIGHT, REFERENCE_WIDTH
from models.overlay import MotionPreset


class Easing(str, Enum):
    """Easing names supported by preview and FFmpeg expression generation."""

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    ELASTIC = "elastic"
    BACK = "back"
    BOUNCE = "bounce"


@dataclass(frozen=True, slots=True)
class MotionSpec:
    """Resolved motion settings for one overlay region."""

    preset: MotionPreset = MotionPreset.NONE
    start: float = 0.0
    end: float = 3.0
    fade_duration: float = 0.35
    pop_duration: float = 0.60
    bounce_duration: float = 2.0
    slide_duration: float = 0.35
    scale_duration: float = 0.60
    speed: float = 1.0
    strength: float = 1.0
    easing: Easing = Easing.EASE_OUT
    bounce_amplitude_ratio: float = 24 / REFERENCE_HEIGHT
    float_x_ratio: float = 18 / REFERENCE_WIDTH
    float_y_ratio: float = 12 / REFERENCE_HEIGHT
    shake_x_ratio: float = 8 / REFERENCE_WIDTH
    shake_y_ratio: float = 6 / REFERENCE_HEIGHT
    elastic_y_ratio: float = 28 / REFERENCE_HEIGHT

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)


@dataclass(frozen=True, slots=True)
class PreviewTransform:
    """Concrete transform values for one preview overlay at one timestamp."""

    x_offset: float = 0.0
    y_offset: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0
    rotation_delta: float = 0.0


class EasingEngine:
    """Numerical and FFmpeg-expression easing helpers shared by both paths."""

    @staticmethod
    def resolve(easing: Easing | str) -> Easing:
        if isinstance(easing, Easing):
            return easing
        value = str(easing).strip().lower().replace("-", "_").replace(" ", "_")
        for item in Easing:
            if item.value == value:
                return item
        return Easing.EASE_OUT

    @staticmethod
    def clip01(value: float) -> float:
        return min(max(value, 0.0), 1.0)

    def apply(self, value: float, easing: Easing | str = Easing.EASE_OUT) -> float:
        p = self.clip01(value)
        easing = self.resolve(easing)
        if easing == Easing.LINEAR:
            return p
        if easing == Easing.EASE_IN:
            return p * p
        if easing == Easing.EASE_OUT:
            return 1.0 - (1.0 - p) * (1.0 - p)
        if easing == Easing.EASE_IN_OUT:
            return 2.0 * p * p if p < 0.5 else 1.0 - pow(-2.0 * p + 2.0, 2) / 2.0
        if easing == Easing.ELASTIC:
            if p in {0.0, 1.0}:
                return p
            return pow(2.0, -10.0 * p) * sin((p * 10.0 - 0.75) * (2.0 * pi / 3.0)) + 1.0
        if easing == Easing.BACK:
            c1 = 1.70158
            c3 = c1 + 1.0
            return 1.0 + c3 * pow(p - 1.0, 3) + c1 * pow(p - 1.0, 2)
        if easing == Easing.BOUNCE:
            n1 = 7.5625
            d1 = 2.75
            if p < 1.0 / d1:
                return n1 * p * p
            if p < 2.0 / d1:
                p -= 1.5 / d1
                return n1 * p * p + 0.75
            if p < 2.5 / d1:
                p -= 2.25 / d1
                return n1 * p * p + 0.9375
            p -= 2.625 / d1
            return n1 * p * p + 0.984375
        return p

    @staticmethod
    def expr(progress: str, easing: Easing | str = Easing.EASE_OUT) -> str:
        p = f"min(max({progress},0),1)"
        easing = EasingEngine.resolve(easing)
        if easing == Easing.LINEAR:
            return p
        if easing == Easing.EASE_IN:
            return f"({p})*({p})"
        if easing == Easing.EASE_OUT:
            return f"1-(1-({p}))*(1-({p}))"
        if easing == Easing.EASE_IN_OUT:
            return f"if(lt({p},0.5),2*({p})*({p}),1-pow(-2*({p})+2,2)/2)"
        if easing == Easing.ELASTIC:
            return f"if(or(eq({p},0),eq({p},1)),{p},pow(2,-10*({p}))*sin((({p})*10-0.75)*(2*PI/3))+1)"
        if easing == Easing.BACK:
            return f"1+2.70158*pow(({p})-1,3)+1.70158*pow(({p})-1,2)"
        if easing == Easing.BOUNCE:
            return (
                f"if(lt({p},1/2.75),7.5625*({p})*({p}),"
                f"if(lt({p},2/2.75),7.5625*(({p})-1.5/2.75)*(({p})-1.5/2.75)+0.75,"
                f"if(lt({p},2.5/2.75),7.5625*(({p})-2.25/2.75)*(({p})-2.25/2.75)+0.9375,"
                f"7.5625*(({p})-2.625/2.75)*(({p})-2.625/2.75)+0.984375)))"
            )
        return p


class MotionEvaluator:
    """Numerically evaluate overlay motion for live preview."""

    easing_engine = EasingEngine()

    @staticmethod
    def preset(motion: MotionPreset | str) -> MotionPreset:
        return motion if isinstance(motion, MotionPreset) else MotionPreset.from_label(str(motion))

    def spec(
        self,
        motion: MotionPreset | str,
        start: float = 0.0,
        end: float | None = None,
        speed: float = 1.0,
        strength: float = 1.0,
        easing: Easing | str = Easing.EASE_OUT,
    ) -> MotionSpec:
        start = max(0.0, float(start))
        resolved_end = max(start + 0.1, float(end)) if end is not None else start + 3.0
        return MotionSpec(
            preset=self.preset(motion),
            start=start,
            end=resolved_end,
            speed=max(0.05, float(speed)),
            strength=max(0.0, float(strength)),
            easing=EasingEngine.resolve(easing),
        )

    def local_time(self, spec: MotionSpec, current_time: float) -> float:
        return max(0.0, (float(current_time) - spec.start) * spec.speed)

    @staticmethod
    def _clip01(value: float) -> float:
        return EasingEngine.clip01(value)

    @staticmethod
    def _with_strength(value: float, strength: float) -> float:
        return 1.0 + (value - 1.0) * strength

    def _ease(self, value: float, spec: MotionSpec) -> float:
        return self.easing_engine.apply(value, spec.easing)

    def opacity_at(self, spec: MotionSpec, local_t: float) -> float:
        fade_duration = max(spec.fade_duration, 0.05)
        if spec.preset in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return self._clip01(local_t / fade_duration)
        if spec.preset == MotionPreset.FADE_OUT:
            fade_t = local_t - max(spec.duration * spec.speed - fade_duration, 0.0)
            return 1.0 - self._clip01(fade_t / fade_duration)
        return 1.0

    def scale_at(self, spec: MotionSpec, local_t: float) -> float:
        if spec.preset in {MotionPreset.POP, MotionPreset.ZOOM}:
            d = max(spec.pop_duration, 0.05)
            if local_t < d * 0.55:
                p = self._ease(local_t / (d * 0.55), spec)
                value = 0.70 + 0.60 * p
            elif local_t < d:
                p = self._ease((local_t - d * 0.55) / (d * 0.45), spec)
                value = 1.30 - 0.30 * p
            else:
                value = 1.0
            return self._with_strength(value, spec.strength)
        if spec.preset == MotionPreset.SCALE:
            return 1.0 + 0.10 * spec.strength * sin(local_t * 4.0)
        if spec.preset == MotionPreset.SCALE_UP:
            p = self._ease(local_t / max(spec.scale_duration, 0.05), spec)
            return self._with_strength(0.80 + 0.20 * p, spec.strength)
        if spec.preset == MotionPreset.SCALE_DOWN:
            p = self._ease(local_t / max(spec.scale_duration, 0.05), spec)
            return self._with_strength(1.20 - 0.20 * p, spec.strength)
        if spec.preset == MotionPreset.PULSE:
            return 1.0 + 0.08 * spec.strength * sin(local_t * 8.0)
        return 1.0

    def offset_at(
        self,
        spec: MotionSpec,
        local_t: float,
        canvas_width: float,
        canvas_height: float,
        overlay_width: float,
        overlay_height: float,
        x_ratio: float = 0.5,
        y_ratio: float = 0.5,
    ) -> tuple[float, float]:
        slide_p = self._ease(local_t / spec.slide_duration, spec)
        base_left = canvas_width * x_ratio - overlay_width / 2
        base_top = canvas_height * y_ratio - overlay_height / 2
        if spec.preset in {MotionPreset.SLIDE, MotionPreset.SLIDE_LEFT}:
            return (canvas_width - base_left) * (1 - slide_p), 0.0
        if spec.preset == MotionPreset.SLIDE_RIGHT:
            return (-overlay_width - base_left) * (1 - slide_p), 0.0
        if spec.preset == MotionPreset.SLIDE_UP:
            return 0.0, (canvas_height - base_top) * (1 - slide_p)
        if spec.preset == MotionPreset.SLIDE_DOWN:
            return 0.0, (-overlay_height - base_top) * (1 - slide_p)
        layout = NormalizedLayoutEngine()
        if spec.preset == MotionPreset.BOUNCE:
            amp_y = layout.denormalize_motion_amplitude(spec.bounce_amplitude_ratio, canvas_height)
            return 0.0, amp_y * spec.strength * sin(local_t * 10.0) * pow(2.718281828, -1.8 * local_t)
        if spec.preset in {MotionPreset.FLOAT, MotionPreset.DRIFT}:
            amp_x = layout.denormalize_motion_amplitude(spec.float_x_ratio, canvas_width)
            amp_y = layout.denormalize_motion_amplitude(spec.float_y_ratio, canvas_height)
            return amp_x * spec.strength * sin(local_t * 1.4), amp_y * spec.strength * cos(local_t * 1.1)
        if spec.preset == MotionPreset.SHAKE:
            amp_x = layout.denormalize_motion_amplitude(spec.shake_x_ratio, canvas_width)
            amp_y = layout.denormalize_motion_amplitude(spec.shake_y_ratio, canvas_height)
            return amp_x * spec.strength * sin(local_t * 42), amp_y * spec.strength * cos(local_t * 55)
        if spec.preset == MotionPreset.ELASTIC:
            amp_y = layout.denormalize_motion_amplitude(spec.elastic_y_ratio, canvas_height)
            return 0.0, amp_y * spec.strength * sin(22 * local_t) * pow(2.718281828, -3 * local_t)
        return 0.0, 0.0

    def rotation_delta_at(self, spec: MotionSpec, local_t: float) -> float:
        if spec.preset == MotionPreset.ROTATE_FLOAT:
            return 6.0 * spec.strength * sin(local_t * 3.0)
        return 0.0


class PreviewTransformEvaluator(MotionEvaluator):
    """Evaluate all preview transform channels at once."""

    def evaluate(
        self,
        spec: MotionSpec,
        current_time: float,
        canvas_width: float,
        canvas_height: float,
        overlay_width: float,
        overlay_height: float,
        x_ratio: float = 0.5,
        y_ratio: float = 0.5,
    ) -> PreviewTransform:
        local_t = MotionEvaluator.local_time(self, spec, current_time)
        x_offset, y_offset = self.offset_at(
            spec,
            local_t,
            canvas_width,
            canvas_height,
            overlay_width,
            overlay_height,
            x_ratio,
            y_ratio,
        )
        return PreviewTransform(
            x_offset=x_offset,
            y_offset=y_offset,
            scale=self.scale_at(spec, local_t),
            opacity=self.opacity_at(spec, local_t),
            rotation_delta=self.rotation_delta_at(spec, local_t),
        )


class FFmpegExpressionBuilder(PreviewTransformEvaluator):
    """Build FFmpeg expressions and expose matching preview helpers."""

    @staticmethod
    def _e(value: str) -> str:
        """Escape expression commas for FFmpeg filtergraph option values."""
        return value.replace(",", r"\,")

    @staticmethod
    def _clip01_raw(value: str) -> str:
        return f"min(max({value},0),1)"

    @staticmethod
    def _clip01_expr(value: str) -> str:
        return FFmpegExpressionBuilder._e(FFmpegExpressionBuilder._clip01_raw(value))

    @staticmethod
    def local_time_expr(start: float = 0.0, speed: float = 1.0) -> str:
        start = max(0.0, float(start))
        speed = max(0.05, float(speed))
        if abs(speed - 1.0) < 0.0001:
            return f"(t-{start:.3f})"
        return f"((t-{start:.3f})*{speed:.4f})"

    # Backward-compatible static name used by older tests/docs.
    local_time = local_time_expr

    def animation(
        self,
        motion: MotionPreset | str,
        start: float = 0.0,
        end: float | None = None,
        speed: float = 1.0,
        strength: float = 1.0,
        easing: Easing | str = Easing.EASE_OUT,
    ) -> MotionSpec:
        return self.spec(motion, start, end, speed, strength, easing)

    def _ease_expr_raw(self, progress: str, easing: Easing | str = Easing.EASE_OUT) -> str:
        return f"({EasingEngine.expr(progress, easing)})"

    def _ease_expr(self, progress: str, easing: Easing | str = Easing.EASE_OUT) -> str:
        return self._e(self._ease_expr_raw(progress, easing))

    def position_expr(
        self,
        x: float,
        y: float,
        motion: MotionPreset,
        start: float,
        end: float,
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> tuple[str, str, str]:
        """Return top-left overlay expressions in final-canvas space."""
        spec = self.animation(motion, start, end, speed, strength)
        base_x = f"W*{x:.4f}-w/2"
        base_y = f"H*{y:.4f}-h/2"
        enable = f"between(t,{spec.start:.3f},{spec.end:.3f})"
        local_t = self.local_time_expr(spec.start, spec.speed)
        slide_p = self._ease_expr(f"{local_t}/{spec.slide_duration:.3f}", spec.easing)
        amp = f"{spec.strength:.4f}"

        if spec.preset in {MotionPreset.SLIDE, MotionPreset.SLIDE_LEFT}:
            return f"W-(W-({base_x}))*{slide_p}", base_y, enable
        if spec.preset == MotionPreset.SLIDE_RIGHT:
            return f"-w+(({base_x})+w)*{slide_p}", base_y, enable
        if spec.preset == MotionPreset.SLIDE_UP:
            return base_x, f"H-(H-({base_y}))*{slide_p}", enable
        if spec.preset == MotionPreset.SLIDE_DOWN:
            return base_x, f"-h+(({base_y})+h)*{slide_p}", enable
        if spec.preset == MotionPreset.BOUNCE:
            return base_x, f"{base_y}+H*{spec.bounce_amplitude_ratio:.6f}*{amp}*sin({local_t}*10)*exp(-1.8*{local_t})", enable
        if spec.preset in {MotionPreset.FLOAT, MotionPreset.DRIFT}:
            return f"{base_x}+W*{spec.float_x_ratio:.6f}*{amp}*sin({local_t}*1.4)", f"{base_y}+H*{spec.float_y_ratio:.6f}*{amp}*cos({local_t}*1.1)", enable
        if spec.preset == MotionPreset.SHAKE:
            return f"{base_x}+W*{spec.shake_x_ratio:.6f}*{amp}*sin({local_t}*42)", f"{base_y}+H*{spec.shake_y_ratio:.6f}*{amp}*cos({local_t}*55)", enable
        if spec.preset == MotionPreset.ELASTIC:
            return base_x, f"{base_y}+H*{spec.elastic_y_ratio:.6f}*{amp}*sin(22*{local_t})*exp(-3*{local_t})", enable
        return base_x, base_y, enable

    def alpha_filter(
        self,
        motion: MotionPreset,
        start: float = 0.0,
        end: float | None = None,
        duration: float = 0.35,
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> str:
        """Return alpha-preserving FFmpeg filters for fade motion."""
        spec = self.animation(motion, start, end, speed, strength)
        duration = max(float(duration) / max(spec.speed, 0.05), 0.05)
        if spec.preset in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return f",format=rgba,fade=t=in:st={spec.start:.3f}:d={duration:.3f}:alpha=1"
        if spec.preset == MotionPreset.FADE_OUT:
            fade_start = max(spec.start, spec.end - duration)
            return f",format=rgba,fade=t=out:st={fade_start:.3f}:d={duration:.3f}:alpha=1"
        return ",format=rgba"

    def _scale_factor_expr(
        self,
        motion: MotionPreset,
        start: float = 0.0,
        end: float | None = None,
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> str:
        spec = self.animation(motion, start, end, speed, strength)
        local_t = self.local_time_expr(spec.start, spec.speed)
        strength_expr = f"{spec.strength:.4f}"

        if spec.preset in {MotionPreset.POP, MotionPreset.ZOOM}:
            first_d = spec.pop_duration * 0.55
            second_d = spec.pop_duration * 0.45
            pop_up = self._ease_expr_raw(f"{local_t}/{first_d:.3f}", spec.easing)
            pop_down = self._ease_expr_raw(f"({local_t}-{first_d:.3f})/{second_d:.3f}", spec.easing)
            raw = (
                f"if(lt({local_t},0),0.70,"
                f"if(lt({local_t},{first_d:.3f}),0.70+0.60*{pop_up},"
                f"if(lt({local_t},{spec.pop_duration:.3f}),1.30-0.30*{pop_down},1.00)))"
            )
            return self._e(f"1+({raw}-1)*{strength_expr}")
        if spec.preset == MotionPreset.SCALE:
            return f"1.00+0.10*{strength_expr}*sin({local_t}*4)"
        if spec.preset == MotionPreset.SCALE_UP:
            progress = self._ease_expr_raw(f"{local_t}/{spec.scale_duration:.3f}", spec.easing)
            raw = f"0.80+0.20*{progress}"
            return self._e(f"1+({raw}-1)*{strength_expr}")
        if spec.preset == MotionPreset.SCALE_DOWN:
            progress = self._ease_expr_raw(f"{local_t}/{spec.scale_duration:.3f}", spec.easing)
            raw = f"1.20-0.20*{progress}"
            return self._e(f"1+({raw}-1)*{strength_expr}")
        if spec.preset == MotionPreset.PULSE:
            return f"1.00+0.08*{strength_expr}*sin({local_t}*8)"
        return "1.00"

    def region_scale_expr(
        self,
        base_width: str,
        motion: MotionPreset,
        start: float = 0.0,
        end: float | None = None,
        base_height: str = "-1",
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> tuple[str, str]:
        """Return dynamic region scale expressions for `scale=eval=frame`."""
        factor = self._scale_factor_expr(motion, start, end, speed, strength)
        if factor == "1.00":
            return base_width, base_height
        width = f"({base_width})*({factor})"
        if base_height == "-1":
            return width, "-1"
        return width, f"({base_height})*({factor})"

    def rotation_expr(self, base_degrees: float, motion: MotionPreset | str, start: float = 0.0, speed: float = 1.0, strength: float = 1.0) -> str:
        preset = self.preset(motion)
        local_t = self.local_time_expr(start, speed)
        if preset == MotionPreset.ROTATE_FLOAT:
            return f"({float(base_degrees):.4f}+6*{max(0.0, float(strength)):.4f}*sin({local_t}*3))*PI/180"
        return f"{float(base_degrees):.4f}*PI/180"

    def preview_alpha(
        self,
        motion: MotionPreset | str,
        local_t: float,
        overlay_duration: float | None = None,
        fade_duration: float = 0.35,
    ) -> float:
        spec = self.spec(motion, 0.0, overlay_duration or 3.0)
        return self.opacity_at(spec, local_t)

    def preview_scale(self, motion: MotionPreset | str, local_t: float, overlay_duration: float | None = None, strength: float = 1.0) -> float:
        spec = self.spec(motion, 0.0, overlay_duration or 3.0, strength=strength)
        return self.scale_at(spec, local_t)

    def preview_offset(
        self,
        motion: MotionPreset | str,
        local_t: float,
        canvas_width: float,
        canvas_height: float,
        overlay_width: float,
        overlay_height: float,
        x_ratio: float = 0.5,
        y_ratio: float = 0.5,
        strength: float = 1.0,
    ) -> tuple[float, float]:
        spec = self.spec(motion, 0.0, 3.0, strength=strength)
        return self.offset_at(spec, local_t, canvas_width, canvas_height, overlay_width, overlay_height, x_ratio, y_ratio)

    def preview_rotation_delta(self, motion: MotionPreset | str, local_t: float, strength: float = 1.0) -> float:
        spec = self.spec(motion, 0.0, 3.0, strength=strength)
        return self.rotation_delta_at(spec, local_t)

    def preview_transform(
        self,
        motion: MotionPreset | str,
        current_time: float,
        start: float,
        end: float,
        canvas_width: float,
        canvas_height: float,
        overlay_width: float,
        overlay_height: float,
        x_ratio: float = 0.5,
        y_ratio: float = 0.5,
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> PreviewTransform:
        spec = self.spec(motion, start, end, speed, strength)
        return self.evaluate(spec, current_time, canvas_width, canvas_height, overlay_width, overlay_height, x_ratio, y_ratio)

    def alpha_expr(self, motion: MotionPreset, duration: float) -> str:
        # Kept for compatibility with older tests/callers; prefer alpha_filter().
        if motion in {MotionPreset.FADE, MotionPreset.FADE_IN}:
            return "if(lt(t,0.35),t/0.35,1)"
        if motion == MotionPreset.FADE_OUT:
            return f"if(gt(t,{max(duration - 0.35, 0):.3f}),max(0,({duration:.3f}-t)/0.35),1)"
        return "1"

    def sticker_scale_expr(
        self,
        scale_ratio: float,
        motion: MotionPreset,
        canvas_width: int,
        start: float = 0.0,
        end: float | None = None,
        speed: float = 1.0,
        strength: float = 1.0,
    ) -> tuple[str, str]:
        target_w = max(1, round(canvas_width * min(max(scale_ratio, 0.01), 1.0)))
        return self.region_scale_expr(str(target_w), motion, start, end, speed=speed, strength=strength)

    def debug_summary(self, motion: MotionPreset | str, start: float, end: float, speed: float = 1.0, strength: float = 1.0) -> str:
        spec = self.spec(motion, start, end, speed, strength)
        scale_expr = self._scale_factor_expr(spec.preset, spec.start, spec.end, spec.speed, spec.strength)
        return (
            f"[MOTION] type={spec.preset.value} speed={spec.speed:.2f} strength={spec.strength:.2f} "
            f"duration={spec.duration:.2f} fade_duration={spec.fade_duration / spec.speed:.3f} "
            f"motion_amplitude_ratio={spec.bounce_amplitude_ratio:.6f} expression=scale:{scale_expr}"
        )


# Backward-compatible names used by existing overlay modules/tests.
OverlayAnimation = MotionSpec
FFmpegMotionBuilder = FFmpegExpressionBuilder
MotionEngine = FFmpegExpressionBuilder
