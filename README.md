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

## Current workflow fixes

- Scene Shuffle now shuffles video frames only. The original audio is extracted before scene detection and reattached to the final export without shuffling audio chunks.
- The queue preview extracts a lightweight thumbnail at `-ss 0.05` and automatically updates when videos are imported or selected.
- Render logs are concise by default (`INFO`, `WARNING`, `ERROR`, `SUCCESS`) and hide FFmpeg frame-by-frame output unless developer debug logging is enabled in code.
- Text template previews show exactly two swatches: text color and background color.

## Additional UI fixes

- Preview overlays can be dragged and snap to the horizontal/vertical canvas center within 10px, showing light-blue guide lines only during snapping.
- Scene Shuffle exposes `Scene Sensitivity` (10-80, default 30) and passes the value to PySceneDetect threshold detection.
- Sticker Overlay includes scale (0.1x-5.0x), rotation (-360° to +360°), and motion presets: None, Fade In, Fade Out, Bounce, Pop, Slide Up, and Slide Down.
- Built-in text templates are locked to the requested seven exact text/background color pairs.

## Unified Social Video Factory workflow

- The app now exposes exactly four mutually exclusive workflow modes: Shuffle + Image, Shuffle + Image + Overlay, Shuffle + Overlay, and Overlay Only.
- The right workflow column includes dedicated controls for pipeline selection, shuffle sensitivity/fallback behavior, image multi-select compositing settings, text templates/motion, sticker properties/motion, and export actions.
- Batch rendering processes each video independently: failed videos are logged and skipped, FFmpeg commands are retried once, and the Stop action terminates active FFmpeg subprocesses safely.
- Render logs include timestamps, workflow status, FFmpeg commands, and stderr tails on failure without continuous frame-by-frame spam during successful renders.

## Layout and workflow UX refactor

- The main editor uses a 3-column layout with a 280-340px left queue/log splitter, a large center preview, and a 360-420px scrollable workflow column.
- The log box lives only at the bottom of the left panel so workflow controls are no longer clipped by render logs.
- Pipeline UI locking is centralized through `PIPELINE_CONFIG`; disabled panels are non-interactive, dimmed, and show a "Disabled in current pipeline" tooltip.
- Shuffle workflow is simplified for mass social production: random shuffle and keep-first-segment are fixed internal defaults.
- Safe areas are normalized via `SafeAreaEngine` with TikTok/Reels/Shorts/Custom presets; text safe width is intentionally narrower than sticker safe width and scales across 720x1280, 1080x1920, and other 9:16 resolutions.
