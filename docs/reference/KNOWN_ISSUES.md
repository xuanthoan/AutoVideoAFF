# KNOWN_ISSUES.md — Active Bugs, Risks, and Follow-Up Items

_Last updated: 2026-05-09_

This file is the quick bug list for future development. For broader context, see `BUGS.md` and `NEXT_SESSION_HANDOFF.md`.

## Critical Issues

### 1. No-Audio Input Can Hang or Fail

Status: open.

Impact:

- Rendering videos without audio can freeze/fail because the pipeline may still assume extracted audio exists or may include audio codec/map args.

Likely files:

- `utils/ffmpeg_helper.py`
- `core/renderer/batch_renderer.py`
- `core/renderer/ffmpeg_builder.py`
- `core/pipeline/base.py`
- `core/pipeline/shuffle_pipeline.py`

Fix summary:

- Probe audio stream before extraction.
- Add explicit `has_audio` handling.
- Build FFmpeg command dynamically.
- Omit audio input/map/codec args for no-audio videos.

Acceptance:

- No-audio videos export video-only MP4 without freeze.
- With-audio videos export with restored original audio.

### 2. Overlay Motion Fade/Pop/Scale Needs Validation

Status: first implementation patch added; real render validation required.

Impact history:

- Text Fade previously did not work.
- Sticker Fade In could disappear.
- Pop previously had little/no visible effect.
- Text Scale previously did not animate.

Current code path:

- Shared `MotionEngine` now generates fade, scale, position, and rotate-float expressions.
- Preview canvas now uses matching motion helpers.
- Needs real FFmpeg output validation.

Likely files:

- `models/overlay.py`
- `core/overlays/motion_engine.py`
- `core/overlays/text_engine.py`
- `core/overlays/sticker_engine.py`
- `gui/preview_canvas.py`
- `gui/workflow_panel.py`

Fix summary:

- Apply animation to immutable overlay regions after asset creation.
- Preserve/multiply original alpha for fade.
- Use per-frame scale/position expressions.
- Keep preview formulas identical to export formulas.

Acceptance:

- Text/sticker Fade works.
- Sticker Fade In does not disappear.
- Pop visibly overshoots.
- Text Scale works in output and preview.

### 3. Pipeline 4 Overlay Only Needs Retest

Status: patched but not fully proven.

Impact:

- Pipeline 4 previously froze when overlay-only graph depended on missing compositor labels or looped PNG inputs did not terminate.

Retest:

- Text only.
- Sticker only.
- Text + sticker.
- With audio.
- Without audio.

## High Priority Risks

### 4. Viewport Fade Needs Real-Media Verification

Status: patched but needs QA.

Risk:

- Fade may be hidden, misaligned, or discontinuous for certain image/overlap values.
- `fade_curve` field may not be fully implemented beyond linear.

Test:

- 720x1280 and 1080x1920.
- Image height 20/35/60.
- Overlap 0/5/20.

### 5. Debug Files Must Stay Developer-Only

Status: partially handled.

Risk:

- `debug_filtergraph.txt` or `debug_fade_filter.txt` could accidentally appear in normal release output.

Acceptance:

- Default `developer_mode=False` render creates only final output and cleaned temp files.

### 6. Font Bundle Missing

Status: open.

Risk:

- Preview/export typography can vary by machine if Montserrat/Poppins are not bundled and explicitly loaded.

Fix:

- Add licensed font files to `assets/fonts/`.
- Ensure renderer loads bundled fonts.

### 7. Template Color Conflict

Status: needs product decision.

Conflict:

- Earlier exact template: `Orange White` background `#F57C4D`.
- Later typography visual tone: approximately `#F58B57`.

Need:

- Decide source of truth.

### 8. Input Indexing Is Fragile

Status: open risk.

Problem:

- Several modules derive FFmpeg input indexes by counting `-i` tokens.

Fix:

- Add explicit `FilterGraph.add_input(args) -> int` helper.

### 9. Text Asset Cache Cleanup Needs Stress Test

Status: risk.

Problem:

- TextEngine caches temp paths while BatchRenderer cleans temp files after each video.

Need:

- Verify cache regenerates correctly after cleanup.

## Medium Priority Items

### 10. Motion UI Is Incomplete

Missing requested presets:

- Float
- Shake
- Slide Left
- Slide Right
- Pulse
- Scale Up
- Scale Down
- Rotate Float

Missing controls:

- Animation Speed slider.
- Animation Strength slider.

### 11. Preview/Export Parity Needs Visual QA

Potential mismatch areas:

- Sticker rotation bounding box.
- Qt preview scaling vs final canvas dimensions.
- Fade alpha behavior.
- Pop/scale motion.
- Timeline visibility and final FFmpeg enable expressions.

### 12. Scene Detection Robustness Needs Media QA

Need to test:

- Videos with very few cuts.
- Very short videos.
- Corrupted/variable frame rate videos.
- Videos with unusual timebases.

### 13. Packaging Is Not Fully Validated

Need to test PyInstaller one-dir build with:

- bundled ffmpeg.exe;
- bundled ffprobe.exe;
- bundled fonts;
- fresh Windows machine.

## Suggested Immediate Bugfix Branch Scope

Best next branch scope:

1. Add no-audio detection/command fix.
2. Add command-level tests for audio/no-audio.
3. Fix motion fade/pop/scale string generation.
4. Add command-level tests for motion filters.

Avoid mixing broad GUI redesign into the same branch.

## Recently Changed — Motion Engine

The Fade/Pop/Scale issue has a first implementation patch, but it still needs media validation.

Validation still required:

- Render text Fade In/Fade Out/Pop/Scale/Pulse.
- Render sticker Fade In/Fade Out/Pop/Rotate Float/Shake/Slide.
- Compare preview and output at the same playhead time.
- Verify transparent sticker edges remain clean during fade.

If failures remain, start with `core/overlays/motion_engine.py` and inspect generated FFmpeg expressions.

## Realtime Motion Preview Status

Status: first implementation added on 2026-05-12.

What is improved:

- Preview and export route through shared motion classes.
- Motion speed/strength affect both preview and output filter expressions.
- Preview emits throttled `[PREVIEW_MOTION]` debug log messages.

Still needs validation:

- Real GUI playback at 30fps-like timer rate.
- Rendered FFmpeg output comparison for all presets.
- Performance check with multiple overlay layers active.

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

