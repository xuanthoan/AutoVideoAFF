"""Built-in text templates; color pickers are intentionally not exposed."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextTemplate:
    name: str
    font_color: str
    box_color: str
    border_color: str
    shadow_color: str
    preview_colors: tuple[str, str, str] = ("#ffffff", "#000000", "#ffff00")
    stroke_width: int = 3
    padding: int = 24


class TemplateManager:
    BUILT_INS = [
        TextTemplate("Impact Pop", "white", "black@0.62", "yellow", "black@0.8", ("#ffffff", "#111111", "#ffff00")),
        TextTemplate("Creator White", "white", "black@0.45", "white", "black@0.6", ("#ffffff", "#333333", "#eeeeee")),
        TextTemplate("Viral Yellow", "yellow", "black@0.68", "white", "black@0.7", ("#ffeb3b", "#111111", "#ffffff")),
        TextTemplate("Clean Black", "black", "white@0.82", "black", "white@0.4", ("#111111", "#ffffff", "#111111")),
        TextTemplate("Neon Pink", "white", "#ff2bd6@0.58", "#00e5ff", "black@0.8", ("#ffffff", "#ff2bd6", "#00e5ff")),
        TextTemplate("Caption Blue", "white", "#1266f1@0.72", "white", "black@0.6", ("#ffffff", "#1266f1", "#ffffff")),
        TextTemplate("Minimal", "white", "black@0.0", "white", "black@0.4", ("#ffffff", "#000000", "#cccccc"), stroke_width=1, padding=8),
    ]

    def names(self) -> list[str]:
        return [template.name for template in self.BUILT_INS]

    def get(self, name: str) -> TextTemplate:
        return next((template for template in self.BUILT_INS if template.name == name), self.BUILT_INS[0])
