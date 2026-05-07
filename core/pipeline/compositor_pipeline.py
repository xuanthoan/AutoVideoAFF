"""Image compositor pipeline module."""
from __future__ import annotations

from core.compositor.image_compositor import ImageCompositor
from core.pipeline.base import FilterGraph, RenderJob


class ImageCompositePipeline:
    name = "image_composite"

    def enabled(self, state) -> bool:
        return state.image_composite.enabled and bool(state.image_composite.image_pool)

    def apply(self, job: RenderJob, graph: FilterGraph) -> FilterGraph:
        image = ImageCompositor.pick_image(job.state.image_composite.image_pool, job.input_path.name)
        graph.inputs.extend(["-loop", "1", "-i", str(image)])
        image_input_index = 1 + (len(graph.inputs) // 4) - 1
        chain, output = ImageCompositor().build_filter(
            video_label=graph.video_label,
            image_label=f"{image_input_index}:v",
            settings=job.state.image_composite,
        )
        graph.add_chain(chain, output)
        return graph
