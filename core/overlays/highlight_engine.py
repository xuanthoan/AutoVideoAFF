"""FFmpeg overlay engine for smart sales highlight text regions."""
from __future__ import annotations

from core.overlays.highlight_library import HighlightStyleManager
from core.overlays.text_engine import TextEngine


class HighlightEngine(TextEngine):
    def __init__(self) -> None:
        super().__init__(templates=HighlightStyleManager(), prefix="highlight")
