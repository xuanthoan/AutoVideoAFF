from __future__ import annotations

from pathlib import Path

from .svg_template_loader import SVGTemplateLoader


class SVGHighlightItem:
    def __init__(self, template_path: Path, text: str, font_size: float | None = None, template_id: str = "") -> None:
        self.template_path = Path(template_path)
        self.template_id = template_id
        self.text = text
        self.font_size = font_size
        self.loader = SVGTemplateLoader(self.template_path)

    def svg_markup(self) -> str:
        markup = self.loader.load_markup()
        self.loader.validate(markup)
        return self.loader.update_dynamic_text(markup, self.text, self.font_size)
