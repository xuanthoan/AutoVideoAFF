"""Module pipeline system orchestration."""
from __future__ import annotations

from pathlib import Path

from core.pipeline.base import FilterGraph, RenderJob
from core.pipeline.compositor_pipeline import ImageCompositePipeline
from core.pipeline.export_pipeline import FinalExportPipeline
from core.pipeline.overlay_pipeline import OverlayPipeline
from core.pipeline.shuffle_pipeline import SceneShufflePipeline
from core.renderer.ffmpeg_builder import FFmpegBuilder
from models.project_state import ProjectState


class PipelineManager:
    """Builds only enabled modules and merges them into one final FFmpeg command."""

    def __init__(self) -> None:
        self.available_modules = [SceneShufflePipeline(), ImageCompositePipeline(), OverlayPipeline(), FinalExportPipeline()]

    def active_modules(self, state: ProjectState):
        return [module for module in self.available_modules if module.enabled(state)]

    def build_command(self, input_path: Path, output_path: Path, state: ProjectState) -> list[str]:
        job = RenderJob(input_path=input_path, output_path=output_path, state=state)
        graph = FilterGraph()
        for module in self.active_modules(state):
            graph = module.apply(job, graph)
        return FFmpegBuilder().build(job, graph)
