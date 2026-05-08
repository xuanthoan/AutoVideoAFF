"""Pipeline primitives for queue-based single-export rendering."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from models.project_state import ProjectState


@dataclass(slots=True)
class FilterGraph:
    inputs: list[str] = field(default_factory=list)
    chains: list[str] = field(default_factory=list)
    video_label: str = "0:v"
    audio_label: str | None = "0:a?"
    extra_args: list[str] = field(default_factory=list)
    temp_files: list[Path] = field(default_factory=list)

    def add_chain(self, chain: str, output_label: str) -> None:
        self.chains.append(chain)
        self.video_label = output_label

    def filter_complex(self) -> str:
        return ";".join(self.chains)


@dataclass(slots=True)
class RenderJob:
    input_path: Path
    output_path: Path
    state: ProjectState
    original_audio_path: Path | None = None
    video_width: int = 1080
    video_height: int = 1920

    @property
    def canvas_size(self) -> str:
        return f"{self.video_width}x{self.video_height}"


class PipelineModule(Protocol):
    name: str

    def enabled(self, state: ProjectState) -> bool: ...

    def apply(self, job: RenderJob, graph: FilterGraph) -> FilterGraph: ...
