from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


class SVGTemplateError(RuntimeError):
    pass


class SVGTemplateLoader:
    def __init__(self, template_path: Path) -> None:
        self.template_path = Path(template_path)

    def load_markup(self) -> str:
        if not self.template_path.exists():
            raise SVGTemplateError(f"SVG template not found: {self.template_path}")
        return self.template_path.read_text(encoding="utf-8")

    def validate(self, markup: str) -> ET.Element:
        try:
            root = ET.fromstring(markup)
        except ET.ParseError as exc:
            raise SVGTemplateError(f"Invalid SVG XML: {exc}") from exc
        if root.tag.split("}")[-1].lower() != "svg":
            raise SVGTemplateError("SVG root element <svg> not found.")
        dynamic = root.find(".//*[@id='dynamic_text']")
        if dynamic is None:
            raise SVGTemplateError("SVG element id='dynamic_text' not found.")
        return root

    @staticmethod
    def update_dynamic_text(markup: str, text: str, font_size: float | None = None) -> str:
        root = ET.fromstring(markup)
        dynamic = root.find(".//*[@id='dynamic_text']")
        if dynamic is None:
            raise SVGTemplateError("SVG element id='dynamic_text' not found.")
        dynamic.text = text or ""
        if font_size is not None:
            dynamic.set("font-size", f"{float(font_size):.2f}")
        return ET.tostring(root, encoding="unicode")
