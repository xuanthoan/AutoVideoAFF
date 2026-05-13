# FILE_STRUCTURE.md — Project File and Module Guide

_Last updated: 2026-05-09_

This file explains what each major file or directory is responsible for. Use it to navigate the codebase quickly.

## Root Files

### `main.py`

PySide6 application entry point. Creates `QApplication`, instantiates `MainWindow`, and starts the GUI event loop.

### `README.md`

User-facing overview and basic project instructions.

### `ARCHITECTURE.md`

Primary architecture reference describing the current implementation, project goals, state model, workflow modes, render graph, GUI, output routing, and known risks.

### `RENDER_PIPELINE.md`

Detailed documentation for the multi-stage logic pipeline and single-final-encode render flow.

### `ANIMATION_SYSTEM.md`

Documentation for overlay coordinates, typography, sticker, motion, preview/export parity, and current animation risks.

### `FFmpeg_PIPELINE.md`

Documentation for FFmpeg/FFprobe discovery, probing, command building, input mapping, filtergraph patterns, and audio/no-audio requirements.

### `PROJECT_STATUS.md`

Current project status, completed features, important recent changes, and next work order.

### `BUGS.md`

Detailed known bug and risk register.

### `NEXT_SESSION_HANDOFF.md`

Compact handoff summary designed to paste into a future chat/session.

### `CURRENT_TASK.md`

Immediate next development priorities and acceptance criteria.

### `DECISIONS.md`

Architecture/product decisions that should not be reversed accidentally.

### `AI_AGENT_RULES.md`

Rules and guardrails for future AI coding agents.

### `TESTING.md`

Test plan, validation matrix, and suggested automated/manual checks.

### `KNOWN_ISSUES.md`

Quick active bug list.

### `AutoVideoAFF.spec`

PyInstaller packaging specification.

### `requirements.txt`

Runtime Python dependencies.

## `models/`

State and data models. These objects are shared by GUI, pipeline, preview, and renderer.

### `models/project_state.py`

Main state model:

- `ProjectState`
- `WorkflowMode`
- `SceneShuffleSettings`
- `ImageCompositeSettings`
- `OverlaySettings`
- `ExportSettings`
- `SafeAreaSettings`

### `models/overlay.py`

Base overlay model and enums/common types such as motion preset and crop focus.

### `models/text_overlay.py`

Text overlay dataclass: text content, template, font size, normalized position, timing, motion.

### `models/sticker_overlay.py`

Sticker overlay dataclass: path, normalized position, normalized canvas-width scale, rotation, timing, motion.

## `core/pipeline/`

Pipeline orchestration and filtergraph primitives.

### `core/pipeline/base.py`

Core render graph primitives:

- `FilterNode`
- `ShuffleSegment`
- `ShufflePlan`
- `LayoutPlan`
- `FilterGraph`
- `RenderJob`
- `PipelineModule`

### `core/pipeline/manager.py`

Selects active modules for the chosen workflow mode and builds the final FFmpeg command.

### `core/pipeline/shuffle_pipeline.py`

Creates video-only scene shuffle graph nodes and stores shuffle metadata.

### `core/pipeline/compositor_pipeline.py`

Adds selected image input and image compositor/fade graph nodes.

### `core/pipeline/overlay_pipeline.py`

Adds text/sticker overlay inputs and graph nodes on top of the current final canvas label.

### `core/pipeline/export_pipeline.py`

Adds final export/codec arguments.

## `core/compositor/`

Image layout and viewport fade implementation.

### `core/compositor/image_compositor.py`

Computes `LayoutPlan` and builds image/video/fade filter nodes. Key file for overlap fade issues.

### `core/compositor/fade_mask.py`

Small fade-mask helper placeholder/module.

## `core/overlays/`

Text, sticker, typography, transform, and motion logic.

### `core/overlays/template_manager.py`

Built-in social text templates and random template selection.

### `core/overlays/typography_engine.py`

Qt/QPainter typography renderer for minimal transparent text PNG regions.

### `core/overlays/text_engine.py`

Renders text assets and builds FFmpeg overlay filters for text regions.

### `core/overlays/sticker_engine.py`

Builds FFmpeg scale/rotate/alpha/overlay filters for sticker assets.

### `core/overlays/motion_engine.py`

Shared motion expression and preview helper logic. Key file for Fade/Pop/Scale bugs.

### `core/overlays/transform.py`

Shared normalized overlay transform helper, including canvas-relative sticker width calculation.

## `core/renderer/`

Batch rendering, command building, and preview frame extraction.

### `core/renderer/batch_renderer.py`

Sequential batch render loop, output paths, audio extraction, process execution, temp cleanup, verification, and logs.

### `core/renderer/ffmpeg_builder.py`

Builds final FFmpeg command from `RenderJob` and `FilterGraph`. Key file for no-audio command bugs.

### `core/renderer/preview_renderer.py`

Extracts first valid preview frame from video using FFmpeg.

## `core/video/`

Scene detection and segmentation utilities.

### `core/video/scene_detector.py`

PySceneDetect wrapper that returns scene segments.

### `core/video/segmenter.py`

Fallback segment generation when scene detection returns too few segments.

### `core/video/concat_engine.py`

Concat-related helper placeholder/module.

### `core/video/timestamp_manager.py`

Timestamp/PTS related constants for FFmpeg command generation.

## `core/safe_area_engine.py`

Computes normalized platform-safe areas and UI exclusion zones for TikTok/Reels/Shorts.

## `core/render_engine.py` and `core/workflow_manager.py`

These files may be introduced later if the project moves toward a higher-level service layer. Current implementation primarily uses `PipelineManager` and `BatchRenderer`.

## `gui/`

PySide6 user interface.

### `gui/main_window.py`

Main app shell, 3-column layout, render thread, state sync, preview/timeline wiring.

### `gui/queue_panel.py`

Video queue UI: add files/folder, remove, clear, select.

### `gui/workflow_panel.py`

Right workflow controls and pipeline-dependent UI locking.

### `gui/preview_canvas.py`

Preview display, safe area drawing, overlay drawing, drag/snap, live text/sticker preview.

### `gui/mini_timeline.py`

Compact overlay-only timeline with playhead, timing blocks, visibility, selection.

### `gui/export_panel.py`

Reusable export panel/control primitives.

### `gui/timeline_panel.py`

Placeholder/light wrapper for timeline panel concepts.

### `gui/toolbar.py`

Toolbar placeholder/basic toolbar component.

## `utils/`

Utility modules.

### `utils/ffmpeg_helper.py`

Finds FFmpeg/FFprobe, validates availability, runs ffprobe helpers. Add `probe_has_audio()` here.

### `utils/file_helper.py`

Output path logic, safe output naming, temporary output naming.

### `utils/process_manager.py`

Subprocess lifecycle wrapper with stop support.

### `utils/image_cache.py`

Image cache helper.

### `utils/logger.py`

Small logging helper.

## `assets/`

Static application assets.

### `assets/fonts/README.md`

Documents expected bundled font files. Actual licensed font files still need to be added.

## `bin/`

Expected location for bundled FFmpeg binaries in local/dev/distribution builds:

- `ffmpeg.exe`
- `ffprobe.exe`

This directory may not be committed depending on binary distribution policy.

## Motion Patch File Responsibilities

The 2026-05-09 motion patch makes these files especially important:

- `models/overlay.py`: canonical list of motion presets.
- `core/overlays/motion_engine.py`: shared FFmpeg and preview motion formulas.
- `core/overlays/text_engine.py`: applies dynamic motion to Qt-rendered text regions.
- `core/overlays/sticker_engine.py`: applies dynamic motion to sticker regions, including rotate-float.
- `gui/preview_canvas.py`: live preview alpha/scale/offset/rotation using `MotionEngine`.
- `gui/workflow_panel.py`: exposes the available motion presets in text/sticker dropdowns.

## `core/motion_engine.py`

Canonical shared motion module introduced for realtime preview/export parity.

Contains:

- `MotionSpec`
- `MotionEvaluator`
- `PreviewTransformEvaluator`
- `FFmpegExpressionBuilder`
- `MotionEngine` compatibility alias

`core/overlays/motion_engine.py` is now a compatibility wrapper that re-exports the shared implementation.

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

