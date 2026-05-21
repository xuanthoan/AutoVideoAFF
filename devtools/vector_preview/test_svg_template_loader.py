from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlight.svg_templates import SVGTemplateLoader, SVGTemplateError


def main() -> int:
    try:
        from PySide6.QtCore import QByteArray, Qt
        from PySide6.QtGui import QGuiApplication, QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
    except Exception as exc:
        print(f"WARN: PySide6 unavailable: {exc}")
        return 0

    app = QGuiApplication.instance() or QGuiApplication(["test_svg_template_loader"])
    template = Path("assets/vector_highlight_templates/orange_quote_template_fixed.svg")
    loader = SVGTemplateLoader(template)

    try:
        markup = loader.load_markup()
        root = loader.validate(markup)
        dynamic = root.find(".//*[@id='dynamic_text']")
        assert dynamic is not None, "dynamic_text missing"
        updated = loader.update_dynamic_text(markup, 'GIẢM 50% & "HOT" <NOW>', font_size=96)
        renderer = QSvgRenderer(QByteArray(updated.encode("utf-8")))
        assert renderer.isValid(), "QSvgRenderer invalid"

        size = renderer.defaultSize()
        image = QImage(max(1, size.width()), max(1, size.height()), QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()

        out = Path("devtools/vector_preview/_orange_quote_svg_test.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        assert image.save(str(out), "PNG"), "failed to save PNG"
        print(f"OK: rendered {out}")
        return 0
    except SVGTemplateError as exc:
        print(f"SVGTemplateError: {exc}")
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        _ = app


if __name__ == "__main__":
    sys.exit(main())
