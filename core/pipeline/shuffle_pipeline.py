"""Scene shuffle pipeline module.

Only video frames are shuffled. Audio is deliberately kept outside the shuffle
concat and reattached from the original timeline by the final FFmpeg command.
"""
from __future__ import annotations

from random import Random

from core.pipeline.base import FilterGraph, RenderJob, ShufflePlan, ShuffleSegment
from core.video.scene_detector import SceneDetector
from models.project_state import TimelineSegment
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
        path_matches = settings.segment_video_path in {None, str(job.input_path)}
        has_manual = bool(settings.manual_segments) and path_matches
        has_auto_cache = bool(settings.auto_segments) and path_matches
        source = "manual" if has_manual else "auto"
        if settings.manual_segments and not path_matches:
            graph.debug_events.append("[SHUFFLE] timeline segments belong to another selected video; using auto scene detect")
        if has_manual:
            timeline_segments = settings.manual_segments
            graph.debug_events.append("[SHUFFLE] manual segment mode active; scene detection skipped")
        elif has_auto_cache:
            timeline_segments = settings.auto_segments
            graph.debug_events.append("[SHUFFLE] using generated auto segment list")
        else:
            scenes = self.detector.detect(job.input_path, settings.sensitivity)
            detected = Segmenter(settings.fallback_min_seconds, settings.fallback_max_seconds).ensure_segments(
                scenes, job.input_path
            )
            timeline_segments = [TimelineSegment(segment.start, segment.end, source="auto") for segment in detected]

        segments = self._enabled_segments(timeline_segments)
        segments = self._shuffle_segments(segments, settings.random_mode, settings.keep_first_segment)

        graph.shuffle_plan = ShufflePlan([ShuffleSegment(segment.start_time, segment.end_time) for segment in segments])
        graph.debug_events.append(
            f"[SHUFFLE] source={source} segment_count={len(segments)} order={graph.shuffle_plan.order_summary}"
        )

        v_labels: list[str] = []
        for idx, segment in enumerate(segments):
            v = f"shv{idx}"
            graph.add_node(
                f"shuffle_trim_{idx}",
                f"[{graph.video_label}]trim=start={segment.start_time:.3f}:end={segment.end_time:.3f},setpts=PTS-STARTPTS[{v}]",
                None,
            )
            v_labels.append(f"[{v}]")
        out_v = "shuffled_v"
        graph.add_node("shuffle_concat", "".join(v_labels) + f"concat=n={len(segments)}:v=1:a=0[{out_v}]", out_v)
        graph.audio_label = "original_audio" if job.original_audio_path else "0:a?"
        graph.extra_args.extend(["-fps_mode", "passthrough", "-fflags", "+genpts", "-shortest"])
        return graph

    def _enabled_segments(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        enabled = [segment.normalized() for segment in segments if segment.enabled and segment.duration > 0.05]
        return enabled or [TimelineSegment(0.0, 0.1, source="manual")]

    def _shuffle_segments(self, segments: list[TimelineSegment], random_mode: bool, keep_first_segment: bool) -> list[TimelineSegment]:
        if not random_mode or len(segments) <= 1:
            return segments
        indexed = list(enumerate(segments))
        locked = {index: segment for index, segment in indexed if segment.locked or (keep_first_segment and index == 0)}
        movable = [segment for index, segment in indexed if index not in locked]
        self.random.shuffle(movable)
        output: list[TimelineSegment] = []
        movable_index = 0
        for index in range(len(segments)):
            if index in locked:
                output.append(locked[index])
            else:
                output.append(movable[movable_index])
                movable_index += 1
        return output
