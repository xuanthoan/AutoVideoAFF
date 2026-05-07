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
        if overlays.text_enabled and overlays.text.active:
            chain, output = self.text_engine.build_filter(graph.video_label, overlays.text)
            graph.add_chain(chain, output)
        if overlays.sticker_enabled and overlays.sticker.active:
            graph.inputs.extend(["-i", str(overlays.sticker.path)])
            sticker_index = 1 + sum(1 for token in graph.inputs if token == "-i") - 1
            chain, output = self.sticker_engine.build_filter(graph.video_label, f"{sticker_index}:v", overlays.sticker)
            graph.add_chain(chain, output)
        return graph
