# TESTING.md — Test Plan and Validation Matrix

_Last updated: 2026-05-09_

This project currently has limited automated coverage. Use this file to guide manual and automated validation for future fixes.

## 1. Baseline Static Check

Run after every code/documentation change that could affect imports:

```bash
python -m compileall core gui models utils main.py
```

Expected result:

- Command exits with code 0.
- No syntax/import errors.

## 2. Command-Generation Unit Tests to Add

The most urgent automated tests should validate FFmpeg command construction without requiring full media renders.

### 2.1 No-Audio Command Test

Given:

- input video has no audio;
- overlay/image/shuffle mode is selected.

Assert command does not contain:

- extracted `.m4a` input;
- `-map N:a:0`;
- `-map 0:a?` if no audio should be included;
- `-c:a`.

Assert command does contain:

- final video map;
- video codec args;
- output path.

### 2.2 With-Audio Command Test

Given:

- input video has audio;
- extracted original audio path exists.

Assert command contains:

- audio input path;
- correct audio input index mapping;
- `-c:a aac`;
- final video map.

### 2.3 Pipeline 4 Command Test

For Overlay Only:

- no image input should be added unless sticker/image overlay requires it;
- no compositor/fade labels should be required;
- base video should be `0:v` or a valid chain from original input;
- looped static text inputs should terminate via `-shortest` or equivalent.

### 2.4 Debug Artifact Gate Test

When `developer_mode=False`:

- no debug files are written.

When `developer_mode=True`:

- debug files may be written.

## 3. Filtergraph Tests to Add

### 3.1 Image/Fade Math

For several canvas sizes and settings, assert generated filtergraph contains expected values.

Suggested cases:

| Canvas | Image % | Overlap % |
| --- | --- | --- |
| 720x1280 | 35 | 5 |
| 1080x1920 | 35 | 5 |
| 1080x1920 | 20 | 0 |
| 1080x1920 | 60 | 20 |

Check:

- numeric `color=s=WxH` size;
- no literal `WxH` placeholder;
- `overlap_h` not zero when overlap is enabled;
- fade crop uses expected `source_y`;
- zero-overlap does not generate invalid crop height.

### 3.2 Overlay Position Expressions

Assert text/sticker overlay expressions use final canvas:

```text
W*x_ratio-w/2
H*y_ratio-h/2
```

Do not accept raw preview pixel coordinates.

### 3.3 Sticker Scale Expressions

Assert sticker width is computed from canvas width and normalized scale ratio.

Example:

- `canvas_width=1080`
- `scale=0.16`
- expected target width about `173` pixels.

### 3.4 Motion Expressions

For Fade/Pop/Scale/Bounce:

- assert generated filter contains time-dependent expression using `t` or local time;
- assert dynamic scale uses `eval=frame`;
- assert fade preserves alpha instead of hiding overlay permanently.

## 4. Manual Render Validation Matrix

Use short 5-15 second vertical clips to keep tests fast.

### 4.1 Audio Matrix

| Pipeline | With audio | No audio |
| --- | --- | --- |
| Pipeline 1 Shuffle + Image | Required | Required |
| Pipeline 2 Shuffle + Image + Overlay | Required | Required |
| Pipeline 3 Shuffle + Overlay | Required | Required |
| Pipeline 4 Overlay Only | Required | Required |

Expected:

- With-audio outputs contain audio.
- No-audio outputs are valid silent/video-only MP4 files.
- No queue freeze.
- No invalid `.m4a` references.

### 4.2 Overlay Motion Matrix

Test for both text and sticker where applicable:

- None
- Fade / Fade In
- Fade Out
- Pop
- Bounce
- Scale
- Drift
- Slide Up
- Slide Down

Expected:

- Preview and output look similar.
- Fade transitions opacity, not visibility only.
- Sticker fade does not disappear permanently.
- Pop visibly overshoots then returns.
- Scale changes region transform, not source PNG generation.

### 4.3 Image Compositor Matrix

Test:

- image height 20%, 35%, 60%;
- overlap 0%, 5%, 20%;
- crop focus top/center/bottom.

Expected:

- Image is not distorted.
- Video is shifted/cropped correctly.
- Fade appears only in overlap region.
- No jump frame at fade boundary.

### 4.4 GUI Smoke Test

Manual checks:

- Add multiple videos.
- Select queue item and confirm preview updates.
- Text edits update preview immediately.
- Sticker selection/scale/rotation updates preview immediately.
- Drag overlay and verify normalized position persists into render.
- Mini timeline playhead hides/shows overlays by timing.
- Render/Stop/Open Output Folder buttons remain visible.

## 5. Suggested Test Assets

Maintain a small local test asset folder outside git or in a future `tests/assets/` if licensing permits:

- `vertical_with_audio_720x1280.mp4`
- `vertical_no_audio_720x1280.mp4`
- `vertical_with_audio_1080x1920.mp4`
- `background_image_1080x600.jpg`
- `sticker_transparent.png`

Do not commit copyrighted sample videos.

## 6. Useful Search Commands

```bash
rg "-map|original_audio|audio_label|c:a|probe" core/renderer core/pipeline utils -n
```

```bash
rg "MotionPreset|alpha_filter|region_scale_expr|eval=frame" core/overlays gui models -n
```

```bash
rg "debug_filtergraph|debug_fade_filter|developer_mode" -n
```

```bash
rg "color=c=black|geq=|crop=w=.*h=.*source" core/compositor core/pipeline -n
```

## 7. Release Readiness Gate

Before calling the app production-ready, all must pass:

- compileall static check;
- command-level tests for audio/no-audio;
- real media render for all four pipelines;
- overlay motion visual QA;
- image/fade visual QA;
- no debug artifacts in default mode;
- output folder correctness with multi-folder input queue;
- stop button kills active FFmpeg process;
- clean Windows machine font/FFmpeg bundle test.

## 8. Motion Patch Tests Added/Required

A command-level smoke test should assert:

- Pop scale expressions contain `0.80`, `1.20`, local time, and escaped FFmpeg expression commas.
- Fade In filter contains `format=rgba` and `fade=t=in:st=<start>:d=0.350:alpha=1`.
- Fade Out starts at `end - 0.350`.
- Text filters use `scale=...:eval=frame` and do not use `drawtext`.
- Sticker Rotate Float uses a dynamic `rotate='<expr>'` expression.

Manual render validation is still required for visual quality and preview/output parity.

## 9. Realtime Motion Preview Tests Added/Required

Command-level tests should verify:

- `MotionSpec` exists and carries speed/strength.
- `PreviewTransformEvaluator.evaluate()` returns changing scale/opacity/offset values over time.
- `FFmpegExpressionBuilder` includes speed/strength values in dynamic expressions when non-default.
- Text/sticker filters pass overlay speed/strength into motion expressions.

Manual GUI tests should verify:

- Pressing Play on the Mini Timeline animates visible text/sticker overlays in preview.
- `[PREVIEW_MOTION]` logs appear for active animated overlays without flooding the log box.
- Preview motion visually matches rendered output for Fade, Pop, Bounce, Pulse, Scale, and Rotate Float.

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

