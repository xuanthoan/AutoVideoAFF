"""Scene shuffle pipeline module.

This module plans segment order without creating an encoded intermediate. Segment
trims are represented as filter_complex trim/concat nodes so the final renderer
still performs one encode at export time.
"""
from __future__ import annotations

from random import Random

from core.pipeline.base import FilterGraph, RenderJob
from core.video.scene_detector import SceneDetector
from core.video.segmenter import Segmenter


class SceneShufflePipeline:
    name = "scene_shuffle"

    def __init__(self, detector: SceneDetector | None = None, random: Random | None = None) -> None:
        self.detector = detector or SceneDetector()
        self.random = random or Random()

    def enabled(self, state) -> bool:
        return state.scene_shuffle.enabled

    def apply(self, job: RenderJob, graph: FilterGraph) -> FilterGraph:
        settings = job.state.scene_shuffle
        scenes = self.detector.detect(job.input_path, settings.sensitivity)
        segments = Segmenter(settings.fallback_min_seconds, settings.fallback_max_seconds).ensure_segments(
            scenes, job.input_path
        )
        if settings.random_mode and len(segments) > 1:
            head, tail = segments[0], segments[1:]
            self.random.shuffle(tail)
            segments = [head, *tail] if settings.keep_first_segment else tail + [head]

        v_labels: list[str] = []
        a_labels: list[str] = []
        for idx, segment in enumerate(segments):
            v = f"shv{idx}"
            a = f"sha{idx}"
            graph.chains.append(
                f"[{graph.video_label}]trim=start={segment.start:.3f}:end={segment.end:.3f},setpts=PTS-STARTPTS[{v}]"
            )
            graph.chains.append(
                f"[0:a]atrim=start={segment.start:.3f}:end={segment.end:.3f},asetpts=PTS-STARTPTS[{a}]"
            )
            v_labels.append(f"[{v}]")
            a_labels.append(f"[{a}]")
        out_v = "shuffled_v"
        out_a = "shuffled_a"
        graph.chains.append("".join(sum(zip(v_labels, a_labels), ())) + f"concat=n={len(segments)}:v=1:a=1[{out_v}][{out_a}]")
        graph.video_label = out_v
        graph.audio_label = out_a
        graph.extra_args.extend(["-vsync", "2", "-fflags", "+genpts"])
        return graph
