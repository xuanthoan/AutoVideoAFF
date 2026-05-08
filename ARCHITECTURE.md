# AutoVideoAFF — Current Architecture Handoff

This document summarizes the current repository architecture so future work can continue without rebuilding the app from scratch.

## 1. Product Shape

AutoVideoAFF is currently implemented as one unified Python desktop application for social-video batch production. The intended product is a PySide6 GUI that orchestrates FFmpeg/FFprobe and PySceneDetect; Python owns UI/state/planning, while FFmpeg owns final rendering/compositing/export.

Current top-level flow:

1. User imports videos into the queue.
2. User selects one workflow mode.
3. GUI syncs controls into `ProjectState`.
4. `BatchRenderer` processes queue sequentially.
5. `PipelineManager` builds enabled pipeline modules.
6. Pipeline modules append structured FFmpeg filter nodes into a `FilterGraph`.
7. `FFmpegBuilder` emits one final FFmpeg command for each video.
8. Output is written to an `output/` folder beside the first queued input video.

## 2. Repository Layout

```text
main.py                         # PySide6 app entry point
models/                         # Serializable workflow/project/overlay state
core/pipeline/                  # Modular render pipeline and render graph primitives
core/compositor/                # Image layout + viewport fade compositing logic
core/overlays/                  # Text/sticker/template/motion/typography engines
core/renderer/                  # Batch renderer, FFmpeg command builder, preview frame extraction
core/video/                     # Scene detection, fallback segmentation, timestamp helpers
core/safe_area_engine.py        # Normalized TikTok/Reels/Shorts safe-area calculations
gui/                            # Main window, queue, workflow panel, preview canvas, mini timeline
utils/                          # FFmpeg lookup/probing, file paths, logging, process management
assets/fonts/                   # Expected bundled font location
AutoVideoAFF.spec               # PyInstaller spec
requirements.txt                # Runtime dependencies
```

## 3. Core Data Model

`ProjectState` is the central object passed from GUI to renderer. It contains:

- `videos`: queue of input video paths.
- `workflow_mode`: one of four mutually exclusive workflows.
- `scene_shuffle`: scene detection/shuffle settings.
- `image_composite`: image pool, crop focus, image height %, overlap %, fade curve.
- `overlays`: text/sticker enable state plus primary overlay and multi-layer lists.
- `export`: output, CRF, preset, auto-open, and developer-mode flags.
- `safe_area`: internal always-on TikTok-style safe area and snap settings.

Overlay positions are normalized ratios (`x`, `y`) in final canvas space, not absolute pixels. Sticker scale is normalized relative to canvas width (`scale=0.16` means target sticker width ≈ 16% of final canvas width).

## 4. Workflow Modes

The current enum supports four workflow modes:

1. **Pipeline 1 — Shuffle + Image**
   - Scene shuffle
   - Image compositor
   - No text/sticker overlay

2. **Pipeline 2 — Shuffle + Image + Overlay**
   - Scene shuffle
   - Image compositor
   - Text/sticker overlay

3. **Pipeline 3 — Shuffle + Overlay**
   - Scene shuffle
   - Text/sticker overlay
   - No image compositor

4. **Pipeline 4 — Overlay Only**
   - Original video as base
   - Text/sticker overlay
   - No shuffle/image/fade stages

`PipelineManager.active_modules()` selects modules from workflow mode, then always appends final export.

## 5. Render Graph Architecture

The renderer has been refactored toward a multi-stage logic pipeline with a single final encode:

- Stages produce metadata/filter graph nodes.
- Stages must not export intermediate MP4/H264/H265 files.
- `FilterGraph` stores:
  - `inputs`
  - named `FilterNode`s
  - current `video_label`
  - optional `audio_label`
  - `extra_args`
  - `temp_files`
  - `shuffle_plan`
  - `layout_plan`
  - `debug_events`

Important classes:

- `FilterNode`: named FFmpeg chain node.
- `ShufflePlan`: metadata list of shuffled segment start/end ranges.
- `LayoutPlan`: canvas/image/overlap/fade coordinate calculations.
- `RenderJob`: input/output/state/audio/video-size bundle.
- `PipelineModule`: protocol implemented by pipeline modules.

## 6. Shuffle Stage

`SceneShufflePipeline` detects scenes using `SceneDetector`, falls back through `Segmenter`, shuffles video-only segments, and appends trim/concat nodes.

Key behavior:

- Keeps first segment by default.
- Shuffles only video; audio is intended to be preserved separately.
- Uses `trim`, `setpts`, and `concat=n=...:v=1:a=0`.
- Adds timestamp args (`-fps_mode passthrough`, `-fflags +genpts`) and `-shortest`.
- Stores a `ShufflePlan` for debug/inspection.

## 7. Image Compositor / Viewport Fade

`ImageCompositor` computes a `LayoutPlan` from the final canvas size:

```text
image_h = image_height_percent * H
overlap_h = overlap_percent * H
visible_video_total = H - (image_h - overlap_h)
offset_y = -(H - visible_video_total)
main_video_h = visible_video_total - overlap_h
image_top = H - image_h
fade_start = image_top
source_y = fade_start - offset_y
```

Current graph intent:

1. Prepare/crop background image.
2. Create transparent/black base canvas.
3. Overlay image at `image_top`.
4. Split video into main/fade sources.
5. Crop main visible region.
6. Crop fade overlap region using `source_y`.
7. Apply alpha with `format=yuva420p,geq=...`.
8. Composite main region and fade strip above the image.

Important known caveat: recent patches changed main-video cropping to avoid hiding the fade strip. This likely fixed visibility, but should be verified on real media because fade/video continuity is sensitive to offset and crop coordinates.

## 8. Overlay Architecture

Text and stickers are intended as final post-composition overlays, not attached to source video pixels.

### Text

Current text export path:

1. `SocialTypographyRenderer` renders a minimal transparent RGBA text bounding-box PNG using Qt/QPainter.
2. `TextEngine` caches static text assets by `(text, template, font_size, canvas_width, canvas_height)`.
3. FFmpeg overlays that minimal PNG region onto final canvas using normalized final-canvas expressions.

This replaced raw `drawtext` to improve preview/export parity.

### Sticker

`StickerEngine` overlays sticker image assets directly. Sticker scale is based on final canvas width via `OverlayTransform.sticker_width_pixels()`.

### Shared Transform

`OverlayTransform` extracts normalized center position, scale ratio, rotation, timing, and motion from text/sticker models for shared preview/export math.

## 9. Motion System

`MotionEngine` currently provides:

- `position_expr()` for slide/bounce/drift-style position expressions.
- `alpha_filter()` for FFmpeg alpha fade filters.
- `region_scale_expr()` for dynamic scale/pop/bounce expressions.
- `preview_alpha()` and `preview_scale()` for Qt preview parity.
- `sticker_scale_expr()` for canvas-width-relative sticker scaling.

Known limitation: motion coverage is incomplete and recently reported as broken for fade/pop/scale. See `BUGS.md`.

## 10. GUI Architecture

Main GUI is in `gui/main_window.py`:

- Left column: `QueuePanel` plus log box inside vertical `QSplitter`.
- Center column: `PreviewCanvas` plus compact `MiniTimeline` below.
- Right column: scrollable `WorkflowPanel`, fixed export/stop/open-output buttons.

### Workflow Panel

`WorkflowPanel` contains compact panels for:

- Pipeline mode
- Shuffle controls
- Image compositor controls
- Text controls
- Sticker controls

Pipeline-dependent UI locking is implemented with `PIPELINE_CONFIG` and panel dimming/disable logic.

### Preview Canvas

`PreviewCanvas`:

- Displays extracted preview frame.
- Draws safe area overlays.
- Draws text/sticker overlays on top of preview.
- Supports normalized drag, safe-area clamping, and center snapping guides.
- Uses shared typography renderer and motion preview helpers.

### Mini Timeline

`MiniTimeline` is lightweight and overlay-only:

- Tracks text/sticker timing blocks.
- Supports playhead, play/pause/stop, drag/resize block timing, visibility toggles.
- Syncs overlay active-at-time behavior with preview.

## 11. Output and Process Management

`BatchRenderer`:

- Sequentially renders queue items.
- Uses `ProcessManager` so Stop can kill current FFmpeg process.
- Creates temp render output `.name.rendering.mp4` then verifies and renames.
- Cleans temporary overlay assets after each video.
- Uses output folder beside the first queued video: `first_video_parent/output/`.
- Skips failed videos and continues batch.

`FFmpegBuilder`:

- Adds input video, graph inputs, optional original audio input.
- Maps final graph video label.
- Adds audio mapping depending on `graph.audio_label` and `original_audio_path`.
- Adds codec args and graph extra args.

## 12. Fonts / Templates

`TemplateManager` contains the exact requested templates plus a `Random Template` option:

1. Orange White — `#FFFFFF / #F58B57` currently (note: earlier requested exact color was `#F57C4D`, later typography request changed visual tone toward `#F58B57`).
2. White Black
3. Pink White
4. Red White
5. Yellow White
6. Pastel Pink
7. Green White

Fonts are expected in `assets/fonts/`. Current implementation can fall back to system fonts if bundled fonts are missing; true production parity requires bundling Montserrat/Poppins font files.

## 13. Debug / Developer Mode

`ExportSettings.developer_mode` exists and defaults to `False`.

Current intent:

- Release mode should output only final video.
- Debug filtergraph files should only be written when developer mode is enabled.

Verify this before release because prior user explicitly asked to avoid `debug_filtergraph.txt` and `debug_fade_filter.txt` in normal output.

## 14. Current Technical Direction

Future work should continue with these principles:

- Do not rebuild the app.
- Keep single final FFmpeg encode per video.
- Keep stages as metadata/filter-graph planning, not intermediate MP4s.
- Keep overlays in final canvas space.
- Keep text rendered as minimal RGBA regions, not full-frame PNG sequences.
- Keep preview and output using shared transform/motion/typography math.
- Make audio optional and command construction dynamic.
