"""Unified text/sticker overlay pipeline module."""
from __future__ import annotations

from core.normalized_layout import NormalizedLayoutEngine
from core.overlays.highlight_engine import HighlightEngine
from core.overlays.sticker_engine import StickerEngine
from core.overlays.text_engine import TextEngine
from core.overlays.watermark_engine import WatermarkEngine
from core.overlays.transform import OverlayTransform
from core.pipeline.base import FilterGraph, RenderJob


class OverlayPipeline:
    name = "overlay"

    def __init__(self) -> None:
        self.text_engine = TextEngine()
        self.watermark_engine = WatermarkEngine()
        self.highlight_engine = HighlightEngine()
        self.sticker_engine = StickerEngine()
        self.layout = NormalizedLayoutEngine()

    def enabled(self, state) -> bool:
        return state.overlays.enabled

    def apply(self, job: RenderJob, graph: FilterGraph) -> FilterGraph:
        overlays = job.state.overlays
        for wm_index, watermark in enumerate(overlays.watermark_overlays(), start=1):
            asset_path = self.watermark_engine.render_asset(
                watermark,
                job.video_width,
                job.video_height,
                temp_files=graph.temp_files,
            )
            graph.debug_events.append(
                f"[OVERLAY] watermark index={wm_index} asset={asset_path.name} density={watermark.density} opacity={watermark.opacity:.2f} region=minimal_bbox"
            )
            graph.debug_events.append(self.layout.debug_font(watermark.effective_font_ratio(), job.video_height))
            for instance_index, instance in enumerate(watermark.instances, start=1):
                graph.inputs.extend(["-loop", "1", "-i", str(asset_path)])
                if "-shortest" not in graph.extra_args:
                    graph.extra_args.append("-shortest")
                watermark_input_index = sum(1 for token in graph.inputs if token == "-i")
                chain, output = self.watermark_engine.build_filter(
                    graph.video_label,
                    f"{watermark_input_index}:v",
                    watermark,
                    instance,
                    suffix=f"_{wm_index}_{instance_index}",
                )
                graph.add_chain(chain, output)
        for index, text_overlay in enumerate(overlays.text_overlays(), start=1):
            asset_path = self.text_engine.render_asset(
                text_overlay,
                job.video_width,
                job.video_height,
                temp_files=graph.temp_files,
            )
            graph.debug_events.append(f"[OVERLAY] text index={index} asset={asset_path.name} region=minimal_bbox")
            graph.debug_events.append(self.layout.debug_font(text_overlay.effective_font_ratio(), job.video_height))
            graph.debug_events.append(self.text_engine.motion.debug_summary(text_overlay.motion, text_overlay.start_time, text_overlay.end_time, text_overlay.motion_speed, text_overlay.motion_strength))
            graph.inputs.extend(["-loop", "1", "-i", str(asset_path)])
            if "-shortest" not in graph.extra_args:
                graph.extra_args.append("-shortest")
            text_index = sum(1 for token in graph.inputs if token == "-i")
            chain, output = self.text_engine.build_filter(
                graph.video_label,
                f"{text_index}:v",
                text_overlay,
                suffix=f"_{index}",
            )
            graph.add_chain(chain, output)
        for index, highlight_overlay in enumerate(overlays.highlight_overlays(), start=1):
            asset_path = self.highlight_engine.render_asset(
                highlight_overlay,
                job.video_width,
                job.video_height,
                temp_files=graph.temp_files,
            )
            graph.debug_events.append(
                f"[OVERLAY] highlight index={index} asset={asset_path.name} style={highlight_overlay.style} region=minimal_bbox"
            )
            graph.debug_events.append(self.layout.debug_font(highlight_overlay.effective_font_ratio(), job.video_height))
            graph.debug_events.append(self.highlight_engine.motion.debug_summary(highlight_overlay.motion, highlight_overlay.start_time, highlight_overlay.end_time, highlight_overlay.motion_speed, highlight_overlay.motion_strength))
            graph.inputs.extend(["-loop", "1", "-i", str(asset_path)])
            if "-shortest" not in graph.extra_args:
                graph.extra_args.append("-shortest")
            highlight_index = sum(1 for token in graph.inputs if token == "-i")
            chain, output = self.highlight_engine.build_filter(
                graph.video_label,
                f"{highlight_index}:v",
                highlight_overlay,
                suffix=f"_{index}",
            )
            graph.add_chain(chain, output)
        for index, sticker_overlay in enumerate(overlays.sticker_overlays(), start=1):
            transform = OverlayTransform.from_overlay(sticker_overlay)
            graph.debug_events.append(
                f"[OVERLAY] sticker index={index} target_width={transform.sticker_width_pixels(job.video_width)} "
                f"center=({transform.x:.3f},{transform.y:.3f}) rotation={transform.rotation:.1f}"
            )
            graph.debug_events.append(self.layout.debug_sticker(transform.scale_ratio, job.video_width))
            graph.debug_events.append(self.sticker_engine.motion.debug_summary(sticker_overlay.motion, sticker_overlay.start_time, sticker_overlay.end_time, sticker_overlay.motion_speed, sticker_overlay.motion_strength))
            graph.inputs.extend(["-loop", "1", "-i", str(sticker_overlay.path)])
            if "-shortest" not in graph.extra_args:
                graph.extra_args.append("-shortest")
            sticker_index = sum(1 for token in graph.inputs if token == "-i")
            chain, output = self.sticker_engine.build_filter(
                graph.video_label,
                f"{sticker_index}:v",
                sticker_overlay,
                suffix=f"_{index}",
                canvas_width=job.video_width,
            )
            graph.add_chain(chain, output)
        return graph
