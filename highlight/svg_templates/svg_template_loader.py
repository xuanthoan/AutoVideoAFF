from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


class SVGTemplateLoader:
    def __init__(self, template_path: Path) -> None:
        self.template_path = Path(template_path)

    def load_markup(self) -> str:
        return self.template_path.read_text(encoding="utf-8")

    @staticmethod
    def update_dynamic_text(markup: str, text: str, font_size: float | None = None) -> str:
        root = ET.fromstring(markup)
        dynamic = root.find(".//*[@id='dynamic_text']")
        if dynamic is None:
            return markup
        dynamic.text = text or ""
        if font_size is not None:
            dynamic.set("font-size", f"{float(font_size):.2f}")
        return ET.tostring(root, encoding="unicode")
