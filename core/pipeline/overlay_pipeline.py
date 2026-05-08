"""Unified text/sticker overlay pipeline module."""
from __future__ import annotations

from core.overlays.sticker_engine import StickerEngine
from core.overlays.text_engine import TextEngine
from core.pipeline.base import FilterGraph, RenderJob


class OverlayPipeline:
    name = "overlay"

    def __init__(self) -> None:
        self.text_engine = TextEngine()
        self.sticker_engine = StickerEngine()

    def enabled(self, state) -> bool:
        return state.overlays.enabled

    def apply(self, job: RenderJob, graph: FilterGraph) -> FilterGraph:
        overlays = job.state.overlays
        for index, text_overlay in enumerate(overlays.text_overlays(), start=1):
            chain, output = self.text_engine.build_filter(graph.video_label, text_overlay, suffix=f"_{index}", temp_files=graph.temp_files)
            graph.add_chain(chain, output)
        for index, sticker_overlay in enumerate(overlays.sticker_overlays(), start=1):
            graph.inputs.extend(["-i", str(sticker_overlay.path)])
            sticker_index = sum(1 for token in graph.inputs if token == "-i")
            chain, output = self.sticker_engine.build_filter(
                graph.video_label,
                f"{sticker_index}:v",
                sticker_overlay,
                suffix=f"_{index}",
            )
            graph.add_chain(chain, output)
        return graph
