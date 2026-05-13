# CURRENT_TASK.md — Current Development Focus

_Last updated: 2026-05-09_

This file defines the immediate work for the next AI/developer session. It is intentionally practical and should be read before editing renderer, overlay, FFmpeg, GUI, or timeline code.

## 1. Current Priority

The project currently has a working architecture scaffold, but it is not production-ready. The next session should focus on runtime correctness, not broad refactoring.

Immediate priority order:

1. Fix no-audio input handling so videos without audio render without freeze/hang.
2. Validate and harden the newly patched overlay animation engine, especially Fade, Fade In, Pop, and Scale for both text and stickers.
3. Verify and harden Pipeline 4 (Overlay Only) on both with-audio and no-audio videos.
4. Verify image compositor overlap fade on real 9:16 media.
5. Add focused command-generation tests before adding new UI features.

## 2. Do Not Work On Yet

Avoid these until the critical runtime bugs are fixed:

- Full NLE-style timeline features.
- Audio waveform or multi-track audio editing.
- Major GUI redesign.
- AI generation features.
- GPU rendering.
- Full-frame RGBA overlay sequences.
- Intermediate MP4 render stages.

## 3. Required Fix 1 — Optional Audio

### Problem

The pipeline has historically assumed that source videos always contain audio and that extracted `.m4a` files always exist. This can make FFmpeg commands invalid or cause queue freezes when input videos are silent/no-audio.

### Expected Behavior

If source video has audio:

- Extract original audio.
- Build visual filtergraph independently.
- Add extracted audio as an input.
- Map final video and extracted audio.
- Encode audio as AAC.

If source video has no audio:

- Skip audio extraction.
- Do not add fake audio.
- Do not add empty `.m4a`.
- Do not map audio.
- Do not add `-c:a`.
- Export video-only MP4.

### Suggested Implementation

- Add `probe_has_audio(path: Path) -> bool` in `utils/ffmpeg_helper.py`.
- Add `has_audio` to `RenderJob` or pass it into `FFmpegBuilder.build()`.
- Refactor `FFmpegBuilder.output_args()` so audio codec args are conditional.
- Ensure `BatchRenderer._extract_original_audio()` is only called when `probe_has_audio()` returns true.
- Add tests for command output with audio and no audio.

## 4. Required Fix 2 — Overlay Motion

### Problem

A first implementation pass now translates motion presets into shared FFmpeg/preview expressions. Real render validation is still required because user-reported symptoms included:

- Text Fade does not work.
- Sticker Fade In can make sticker disappear.
- Pop has no visible effect.
- Text Scale does not work.

### Expected Behavior

- Motion is applied after immutable overlay asset creation.
- Text/sticker source assets remain static minimal regions.
- FFmpeg applies alpha/scale/position/rotation dynamically per frame.
- Preview uses the same formulas as export.
- Fade preserves original PNG/sticker alpha by multiplying motion alpha, not overwriting alpha.

### Suggested Implementation

- Expand `MotionEngine` into a single source of truth for export and preview formulas.
- Use per-frame evaluation for dynamic transforms.
- Verify scale expressions include `eval=frame`.
- Make Pop obvious: roughly `0.80 -> 1.20 -> 1.00` over a short duration.
- Add tests that inspect generated filtergraph strings for fade, pop, and scale behavior.

## 5. Required Fix 3 — Pipeline 4 Overlay Only

Pipeline 4 must be independent from shuffle/image/fade stages.

Correct Pipeline 4 behavior:

1. Input video is base video.
2. Text/sticker overlays are applied on top.
3. Output video is encoded.
4. No image compositor stage is called.
5. No fade stage is called.
6. No missing intermediate label is assumed.

Retest combinations:

- Text only.
- Sticker only.
- Text + sticker.
- Video with audio.
- Video without audio.
- Stop during render.

## 6. Required Fix 4 — Image/Fade Validation

The overlap fade has been patched but still needs real-media validation.

Test cases:

- 720x1280 and 1080x1920 videos.
- Image height 20%, 35%, 60%.
- Overlap 0%, 5%, 20%.
- Crop focus top, center, bottom.

Expected result:

- Fade is visible.
- Fade uses the shifted video region overlapping the image.
- Fade is not hidden behind the main video.
- No frame jump at the overlap boundary.

## 7. Acceptance Criteria for Next Session

A session can be considered successful if it completes at least one of these:

- Adds robust no-audio command handling with tests.
- Fixes text/sticker Fade/Pop/Scale filtergraph behavior with tests.
- Verifies Pipeline 4 with command-level tests for audio/no-audio.
- Adds sample-media render tests for fade and overlay-only output.

## 8. Files to Open First

For optional audio:

- `utils/ffmpeg_helper.py`
- `core/renderer/batch_renderer.py`
- `core/renderer/ffmpeg_builder.py`
- `core/pipeline/base.py`
- `core/pipeline/shuffle_pipeline.py`

For motion:

- `models/overlay.py`
- `core/overlays/motion_engine.py`
- `core/overlays/text_engine.py`
- `core/overlays/sticker_engine.py`
- `gui/preview_canvas.py`
- `gui/workflow_panel.py`

For fade:

- `core/compositor/image_compositor.py`
- `core/pipeline/compositor_pipeline.py`

## 9. Current Non-Negotiables

- Keep the single final encode architecture.
- Keep overlays in final-canvas normalized coordinate space.
- Keep text rendering as minimal Qt/QPainter RGBA regions.
- Keep sticker scale canvas-width-relative.
- Keep output folder beside the first queued input video.
- Keep safe area and snap enabled internally by default.

## 10. Update After Motion Patch — 2026-05-09

The first code pass for the overlay animation engine has been implemented.

What changed:

- `MotionPreset` includes more social motion presets.
- `MotionEngine` now owns shared FFmpeg/preview formulas.
- Text/sticker engines apply motion after overlay asset creation.
- Preview canvas applies matching alpha/scale/offset/rotate-float helpers.

Next task:

- Validate the new motion filters with real FFmpeg renders.
- Fix optional no-audio command handling next; it remains the highest unresolved runtime bug.

## 11. Update After Realtime Motion Preview Patch — 2026-05-12

Realtime motion preview has been implemented without changing the region-only RGBA pipeline.

What changed:

- Added `core/motion_engine.py` with `MotionSpec`, `MotionEvaluator`, `PreviewTransformEvaluator`, and `FFmpegExpressionBuilder`.
- Preview canvas now evaluates motion transforms from the current playhead timestamp.
- Text/sticker speed and strength controls now affect both preview and export.
- `[PREVIEW_MOTION]` debug log messages are emitted for animated visible overlays.

Next highest priority remains the optional no-audio render fix.

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

