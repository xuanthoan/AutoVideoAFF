# AutoVideoAFF — Project Status

## 1. Current State Summary

The repository currently contains a working scaffold/prototype of a unified mass-production social-video desktop app. It includes a PySide6 GUI, queue-based batch rendering, four workflow modes, scene shuffle planning, image compositing, final-canvas overlays, Qt-rendered typography assets, sticker overlays, safe-area/snap preview behavior, mini timeline timing controls, output path handling, and PyInstaller packaging metadata.

The project is not production-complete. The architecture has the intended shape, but several critical runtime issues remain around optional audio, overlay animation, and real-media verification.

## 2. Completed / Implemented Features

### Application and GUI

- PySide6 app entry point in `main.py`.
- Main desktop window with three-column layout:
  - Left: video queue + log box.
  - Center: preview canvas + mini timeline.
  - Right: scrollable workflow controls + fixed render/stop/open-output buttons.
- Video queue supports adding files/folders, removal, clearing, and selection preview.
- Log box shows timestamped render/progress messages.
- Stop button is wired to `ProcessManager.stop_all()` through `BatchRenderer.stop()`.

### Workflow Modes

- Four mutually exclusive modes exist:
  - Pipeline 1: Shuffle + Image
  - Pipeline 2: Shuffle + Image + Overlay
  - Pipeline 3: Shuffle + Overlay
  - Pipeline 4: Overlay Only
- `PipelineManager.active_modules()` selects modules according to workflow mode.
- Right-panel controls are pipeline-locked/dimmed through centralized `PIPELINE_CONFIG` in `WorkflowPanel`.

### Batch Rendering

- Sequential batch render loop exists.
- Per-video temp output is created then verified before final rename.
- Failed video should be skipped while queue continues.
- Output folder is now beside the first queued input video: `first_input_folder/output/`.
- Safe output naming avoids overwriting existing files.

### FFmpeg / FFprobe Integration

- `utils.ffmpeg_helper` locates bundled `bin/ffmpeg(.exe)` / `ffprobe(.exe)`, app root, cwd, and PATH.
- FFmpeg/FFprobe validation fails early with actionable messages.
- `probe_video_size()` and `probe_duration()` exist.
- `ProcessManager` captures subprocess output and can terminate active process.

### Scene Shuffle

- PySceneDetect wrapper exists.
- Fallback segmentation exists for videos with too few scenes.
- Shuffle keeps first segment and shuffles the rest by default.
- Shuffle stage creates video-only trim/concat nodes and should not shuffle audio.
- Shuffle stores `ShufflePlan` metadata and debug events.

### Image Compositor and Fade

- Image compositor supports dynamic image height %, overlap %, crop focus, and fade curve field.
- Compositor computes `LayoutPlan` based on canvas width/height.
- Intended layer order is base canvas → image → main video → fade overlay.
- Fade crop uses viewport-mapped `source_y = fade_start - offset_y`.
- Zero-overlap path bypasses fade generation.

### Text Overlay

- Text overlays use Qt/QPainter rendered minimal RGBA region PNGs, not FFmpeg `drawtext`.
- `SocialTypographyRenderer` is shared by preview/export.
- Text asset cache avoids re-rendering identical static text PNG regions within command construction.
- Multiline text background/padding/radius is handled in Qt renderer.
- Background box shadow was removed; boxes are flat rounded rectangles.

### Sticker Overlay

- Sticker overlay supports source file, normalized x/y, canvas-width-relative scale ratio, rotation, timing, and motion enum.
- Export scale is based on final canvas width, not source image size or preview widget pixels.
- Preview uses matching normalized canvas-space logic.

### Overlay Coordinate System

- Overlay positions are stored as normalized final-canvas ratios.
- Preview canvas maps normalized ratios into displayed canvas rect.
- Export maps normalized ratios into FFmpeg final output canvas expressions.
- Safe-area clamping and snap behavior operate in canvas ratio space.

### Mini Timeline

- Compact mini timeline exists below preview.
- Supports overlay items for text and sticker, playhead, basic controls, timing drag/resize, selected block highlight, and visibility toggles.
- Overlay visibility in preview respects current playhead time.

### Templates

- Built-in social templates exist.
- Template dropdown includes `Random Template`.
- Per-video random template selection exists with immediate-repeat avoidance.

### Packaging / Docs

- `README.md` exists with project overview and workflow notes.
- `AutoVideoAFF.spec` exists for PyInstaller one-dir build.
- `assets/fonts/README.md` documents expected font bundle location.
- `requirements.txt` includes PySide6 and PySceneDetect.

## 3. Important Recent Changes

### Multi-Stage Logic Pipeline

The project moved away from a single procedural string builder and toward structured graph planning:

- `FilterGraph`
- `FilterNode`
- `ShufflePlan`
- `LayoutPlan`
- staged pipeline modules

The actual render is still a single FFmpeg command and should remain that way.

### Final-Canvas Overlay Direction

Text/stickers are intended to be final post-composition overlays. They should be applied after shuffle/image/fade layout, not before viewport shifts.

### Minimal Overlay Asset Direction

Text is rendered as a minimal bounding-box RGBA asset, not full-frame 1080x1920 PNG. Animated overlays should transform that region in FFmpeg, not regenerate full-frame sequences.

### Developer Debug Mode

Debug filtergraph output should be gated behind `ExportSettings.developer_mode`; default is off.

## 4. Current Quality Level

Current project status is best described as:

- Architecture: mostly in place.
- GUI workflow: mostly in place.
- Static overlays: partially working / needs real-media verification.
- Image compositor/fade: recently patched / needs real-media verification.
- Motion effects: first implementation patch added; needs real-render validation.
- Audio handling: known critical risk for no-audio inputs.
- Production readiness: not ready until known bugs are fixed and tested on real videos.

## 5. Recommended Next Work Order

1. Fix optional audio detection and dynamic FFmpeg audio command building.
2. Fix overlay animation engine for fade/pop/scale/bounce/slide preview-output parity.
3. Verify Pipeline 4 overlay-only on no-audio and with-audio videos.
4. Verify image compositor fade on real 720x1280 and 1080x1920 media.
5. Add focused automated tests for FFmpeg command construction.
6. Add small sample-media integration tests if possible.
7. Bundle actual Montserrat/Poppins font files.
8. Re-check release mode creates no debug artifacts.

## 6. Handoff Notes for Next Chat

- Do not rebuild the app; continue modifying existing modules.
- Most urgent files for bug fixes:
  - `utils/ffmpeg_helper.py`
  - `core/renderer/batch_renderer.py`
  - `core/renderer/ffmpeg_builder.py`
  - `core/overlays/motion_engine.py`
  - `core/overlays/text_engine.py`
  - `core/overlays/sticker_engine.py`
  - `core/compositor/image_compositor.py`
  - `gui/preview_canvas.py`
- Keep output path logic: first input video folder + `/output`.
- Keep all overlays in normalized final-canvas space.
- Keep text as minimal Qt-rendered RGBA region assets.
- Keep single final encode; no temp MP4 stages.

## 7. Update — Overlay Motion Patch 2026-05-09

A first implementation pass for overlay motion has been added.

Status changes:

- Motion architecture: improved but needs real FFmpeg render validation.
- Fade/Pop/Scale: command-generation behavior improved; visual QA still required.
- No-audio handling: still open and should remain the next highest priority.

## 8. Update — Realtime Motion Preview 2026-05-12

Realtime motion preview has been implemented at the architecture/code level.

Status changes:

- Motion preview: now uses shared evaluator and current playhead timestamp.
- Motion speed/strength: now stored in overlay state and passed to export expressions.
- Motion QA: still requires real GUI playback and FFmpeg render comparison.
- No-audio handling: still open and remains the next critical fix.

## Smart Highlight System Update

- Added an independent sales/CTA highlight text layer separate from main text and stickers.
- Layer order is now: base video/image composite -> main text -> highlight text -> sticker (watermark slot remains reserved before text when implemented).
- Highlight uses minimal RGBA region rendering through the shared Qt typography renderer and the same FFmpeg overlay/motion expression path as text; do not replace it with drawtext or full-frame RGBA overlays.
- Highlight position is stored as normalized x/y coordinates and is moved by dragging the highlight region directly on the preview canvas.
- Highlight style randomization may change style colors/box/border/glow presets only; it must never randomize position.
- Sales wording presets live in `core/overlays/highlight_library.py`; highlight model state lives in `models/highlight_overlay.py`; export is handled by `core/overlays/highlight_engine.py`.
- Remaining validation: visual QA with PySide6 + FFmpeg should compare preview/output for highlight styles, alpha, pop/bounce/pulse/shake/rotate motion, and drag-position parity.

## Text Watermark System Update

- Added an independent text watermark layer for anti-reupload and lightweight branding. It is not a primary text/sticker/highlight overlay and may run even in Pipeline 1 when enabled.
- Layer order is now: video/image composite -> watermark text regions -> main text -> highlight text -> sticker.
- Watermark settings include enable, text, font, responsive font size, font color, true alpha opacity, rotation, random position, slow floating motion, and density: single, multi-light, multi-medium, multi-heavy.
- Watermark export uses minimal transparent text regions with `format=rgba,colorchannelmixer=aa=...`, optional slow float expressions, and rotate/overlay filters; do not replace this with full-frame RGBA canvases.
- Batch render randomizes watermark X/Y, slight rotation, motion phase/direction, scale, and opacity per video using a deterministic per-video seed for preview/export parity.
- Safe placement keeps a 5% edge margin and avoids primary text, highlight, and sticker centers where possible.
- Realtime preview renders the same minimal text regions with matching font size, color, opacity, rotation, scale, density, and slow floating motion.
- Remaining validation: visual QA should compare preview/output across 720x1280, 1080x1920, and 1440x2560, especially multi-heavy density and Pipeline 1 watermark-only renders.

## Professional Mass Production Editor Layout Update

- Rebuilt the GUI around the required three-column editor layout: compact left Video Queue + Log, priority center Preview Canvas + Timeline, and a wider right Workflow Settings panel.
- Right Workflow Settings now uses two always-visible internal columns: Pipeline/Shuffle/Image/Watermark on the left and Text/Highlight/Sticker/Export on the right; no collapsible sections or hidden tabs were introduced.
- Export controls (`Render Video`, `Stop`, `Open Output Folder`) now live inside the right Export group so they remain part of the settings column instead of requiring a separate window-level scroll area.
- Replaced long motion speed sliders with compact dropdowns (`0.25x`, `0.5x`, `0.75x`, `1x`, `1.25x`, `1.5x`, `2x`, `3x`) and replaced text/sticker motion strength sliders with numeric `x` spinboxes defaulting to `1x`.
- Image defaults and labels now match the professional editor spec: Crop Focus = center, Overlap = 10%, Fade Curve = smooth, labels use full names (`Crop Focus`, `Image Height`, `Fade Curve`).
- Left queue buttons use full labels (`Add Video`, `Add Folder`, `Remove Selected`, `Clear All`) with compact 30–34px button styling, and the log box remains entirely in the left panel.
- Remaining validation: visual QA with PySide6 should confirm laptop/desktop responsiveness, no overlapped buttons, visible export controls, and usable preview/timeline drag interactions.

## UI/UX Preview Timeline Patch Update

- Added manual cut history controls: `Undo Cut`, `Redo Cut`, and `Clear Manual Cuts`, backed by dedicated `manual_cut_undo_stack` and `manual_cut_redo_stack` state in the main window.
- Preview playback now updates the base video frame from a low-FPS frame cache on the same playhead time source used by text, sticker, highlight, and watermark motion.
- Watermark settings were simplified in the GUI: random position, slow floating motion, and -15° rotation remain internal defaults and are no longer exposed as controls.
- Text and Highlight inputs now use separate signal handlers, and timeline list refreshes no longer emit selection/focus changes while rebuilding rows.
- Highlight text now has a responsive `Highlight Font Size` control wired to realtime preview and final render through the existing normalized font-size model.
- Watermark and Highlight enable checkboxes auto-enable when non-empty text is entered, while empty text still prevents rendering.
- Right settings scrolling was tightened by disabling horizontal scrolling, using equal internal column stretches, and letting controls/text edits expand within their column instead of forcing oversized widths.
- Remaining validation: visual QA should confirm preview video playback, manual cut undo/redo/clear behavior, independent text/highlight typing focus, and no horizontal scrollbar in the right settings panel.

## Preview Performance + Multi Highlight Update

- Preview playback now uses a lightweight cached frame sequence at 12 FPS and updates the base video layer from cached frames instead of launching FFmpeg on each timer tick.
- Overlay preview updates during playback are limited to playhead/time transforms; text, highlight, and watermark assets remain cached unless their content/style settings change.
- Removed `Enable Watermark` and `Enable Highlight` checkboxes from the GUI. Watermark renders when Watermark Text is non-empty; highlights render per layer when that highlight text is non-empty.
- Watermark and Highlight are global overlay features and can activate the overlay pipeline in all workflow modes, including Pipeline 1.
- Highlight now supports multiple independent layers with Add Highlight, Duplicate Highlight, Remove Selected Highlight, a compact highlight list, independent position/timing, and timeline rows (`Highlight 1`, `Highlight 2`, ...).
- Preview supports all active highlight layers and shows a selection outline for the selected highlight. Dragging a selected highlight stores normalized x/y coordinates per highlight layer.
- Panel visuals now use subtle dark boxed group styles instead of dashed title separators, with muted per-panel colors for professional grouping.
- Remaining validation: run visual QA for smooth playback, multi-highlight preview/render parity, global Pipeline 1 watermark/highlight rendering, and no regressions to text/sticker/batch render.

