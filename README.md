# AutoVideoAFF

Unified Python desktop app architecture for mass TikTok/Reels/Shorts video production.

## Goals

- One PySide6 desktop app, not separate tools.
- Modular queue-based pipeline system.
- Scene shuffle, image compositing, text overlay, sticker overlay, motion, preview, and batch export.
- Single final FFmpeg encode: enabled modules append to one `filter_complex` graph before final export.
- AI-ready structure for future subtitle, title, sticker randomization, caption timing, and auto-layout modules.

## Project layout

```text
main.py
core/pipeline/          module pipeline system
core/video/             scene detection, segmentation, timestamps
core/compositor/        image compositor and fade mask logic
core/overlays/          text, sticker, motion, typography, templates
core/renderer/          ffmpeg builder, preview, batch renderer
models/                 project and overlay state
gui/                    PySide6 main window and panels
utils/                  ffmpeg, file, logging, image cache helpers
assets/                 fonts, templates, stickers
bin/                    optional bundled ffmpeg.exe / ffprobe.exe
```

## Build

```bash
pyinstaller --noconfirm --onedir --windowed main.py
```

Or use the included `AutoVideoAFF.spec` to bundle `assets/` and `bin/`.

## FFmpeg setup

Rendering validates both `ffmpeg` and `ffprobe` before starting a batch. Put `ffmpeg.exe` and `ffprobe.exe` in `bin/`, or install FFmpeg globally and add it to `PATH`.

Output files are written with absolute paths under the app's `output/` directory by default. During render the app writes to a hidden `.rendering.mp4` file, verifies it with `ffprobe`, and only then renames it to the final `.mp4` to avoid exposing partial/corrupt files.
