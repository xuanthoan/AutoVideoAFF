# AutoVideoAFF — Known Bugs and Risk Register

This file records known bugs, suspected causes, and suggested fix direction for the current codebase.

## Critical Bugs

### 1. Pipeline can hang/fail with input videos that have no audio

**Status:** Known critical bug / not fully fixed.

**Symptom:**

- User reported render pipeline freezes/hangs when input video has no audio.
- Previous implementation assumed extracted audio always exists and audio mapping is always valid.

**Likely affected files:**

- `core/renderer/batch_renderer.py`
- `core/renderer/ffmpeg_builder.py`
- `core/pipeline/shuffle_pipeline.py`
- `utils/ffmpeg_helper.py`

**Current code risk:**

- `BatchRenderer` attempts audio extraction for shuffle workflows.
- `_extract_original_audio()` can return `None` if stderr indicates no audio.
- `SceneShufflePipeline` sets `graph.audio_label` to `0:a?` when no original audio path exists.
- `FFmpegBuilder` can still add optional audio mapping and `FFmpegBuilder.output_args()` always contains `-c:a aac`.
- There is no explicit `has_audio` field in `RenderJob` / `build_command()`.

**Required fix direction:**

1. Add `probe_has_audio(path: Path) -> bool` using ffprobe stream detection.
2. Add `has_audio: bool` to `RenderJob` or pass into `FFmpegBuilder.build()`.
3. Refactor command building to be truly dynamic:
   - If audio exists and extracted audio path exists: add audio input, map that audio, add `-c:a aac`.
   - If audio does not exist: do not add audio input, do not map audio, do not add audio codec args.
4. Avoid fake audio (`anullsrc`, silent track, empty m4a).
5. Ensure all visual filtergraph stages are independent of audio.
6. Add tests for with-audio and no-audio commands.

**Acceptance criteria:**

- No-audio video exports video-only MP4.
- With-audio video exports MP4 with restored original audio.
- No FFmpeg command contains missing `.m4a` input or invalid `-map N:a:0` when audio is absent.

---

### 2. Overlay animation engine is incomplete / broken for Fade, Pop, Scale

**Status:** First implementation patch added / requires real FFmpeg validation.

**User-reported symptoms:**

- Text Fade motion does not work.
- Sticker Fade In can make sticker disappear.
- Pop motion has little/no visible effect.
- Text Scale motion does not work.

**Likely affected files:**

- `core/overlays/motion_engine.py`
- `core/overlays/text_engine.py`
- `core/overlays/sticker_engine.py`
- `gui/preview_canvas.py`
- `models/overlay.py`
- `gui/workflow_panel.py`

**Current code status:**

- Motion enum now includes the requested common presets (Float, Shake, Slide Left/Right, Pulse, Rotate Float, Scale Up/Down).
- `MotionEngine.alpha_filter()` applies FFmpeg RGBA alpha fades after asset creation.
- Dynamic scale expressions use `scale=...:eval=frame` and are shared by text/sticker engines.
- Preview uses `MotionEngine` helper methods for alpha, scale, offset, and rotate-float behavior.
- Real FFmpeg render validation is still required for every preset.

**Required fix direction:**

1. Create/expand a unified overlay animation model with:
   - fade in/out
   - pop
   - bounce
   - scale up/down
   - float
   - shake
   - slide left/right/up/down
   - pulse
   - rotate float
   - speed/strength parameters if GUI is expanded.
2. Apply animation after immutable overlay asset creation, before final overlay composite.
3. For fade, multiply original alpha by motion alpha; do not overwrite alpha with zero.
4. Use `eval=frame` for dynamic scale/position/rotation filters.
5. Ensure preview uses the same formulas/easing as export.
6. Add tests asserting generated FFmpeg expressions contain dynamic `t`, `eval=frame`, and expected fade/scale filters.

**Acceptance criteria:**

- Sticker Fade In fades from transparent to visible without disappearing.
- Text Fade works.
- Pop visibly overshoots and returns to normal.
- Text Scale applies dynamic region transform, not source PNG regeneration.
- Preview and output motion visually match.

---

### 3. Viewport overlap fade needs real-media verification

**Status:** Recently patched / needs validation.

**Symptom history:**

- Fade overlap disappeared completely after graph refactor.
- Patch changed main video crop so opaque video does not hide fade strip.

**Likely affected files:**

- `core/compositor/image_compositor.py`
- `core/pipeline/compositor_pipeline.py`

**Current code behavior:**

- Calculates `LayoutPlan` dynamically.
- Uses separate `main_src` and `fade_src` from a split.
- Crops main region and fade region separately.
- Applies alpha with `format=yuva420p,geq=...`.
- Composites fade strip at `fade_start`.

**Remaining risk:**

- Main video crop/overlay may alter continuity around overlap region.
- `source_y` clamping may hide math mistakes for extreme layout settings.
- Fade curve setting exists but current geq expression appears linear.

**Required fix direction:**

1. Test with real 720x1280 and 1080x1920 videos.
2. Verify fade is exactly the video area over the image after offset.
3. Implement `fade_curve` variants if not already active.
4. Add command-level unit tests for multiple IH/OV values.

---

## High Priority Bugs / Gaps

### 4. Debug artifact output must remain disabled in release mode

**Status:** Partially handled.

**Files:**

- `models/project_state.py`
- `core/renderer/batch_renderer.py`

**Current behavior:**

- `ExportSettings.developer_mode` exists and defaults to `False`.
- Debug file writers are called only inside `if render_state.export.developer_mode`.

**Risk:**

- Need real render verification that no `debug_filtergraph.txt` or `debug_fade_filter.txt` appears in normal output.

---

### 5. Template color inconsistency

**Status:** Needs decision.

**Details:**

- Earlier requirement specified `Orange White` background `#F57C4D`.
- Later typography requirement requested visual tone approximately `#F58B57`.
- Current code likely uses the later visual tone.

**Files:**

- `core/overlays/template_manager.py`
- `core/overlays/typography_engine.py`

**Fix direction:**

- Decide whether exact template definitions or later visual typography tone wins.
- If exact templates are required, revert `Orange White` to `#F57C4D`.

---

### 6. Font parity depends on actual bundled fonts

**Status:** Incomplete until assets are added.

**Files:**

- `assets/fonts/README.md`
- `core/overlays/typography_engine.py`
- `AutoVideoAFF.spec`

**Risk:**

- If Montserrat/Poppins files are missing, Qt may use fallback fonts, reducing preview/export consistency across machines.

**Fix direction:**

- Add licensed font files to `assets/fonts/`.
- Ensure `SocialTypographyRenderer` explicitly loads the bundled font file.
- Test on a clean Windows machine.

---

### 7. FFmpeg output args are not cleanly separated for no-audio vs audio

**Status:** Related to Critical Bug #1.

**Files:**

- `core/renderer/ffmpeg_builder.py`

**Current risk:**

- `output_args()` always includes `-c:a aac`.
- `ratio_filters` variable is unused.
- Command builder should be refactored to `build_ffmpeg_command(has_audio: bool)` or equivalent.

---

### 8. Motion UI does not expose all requested presets/speed/strength

**Status:** Incomplete.

**Files:**

- `models/overlay.py`
- `gui/workflow_panel.py`
- `core/overlays/motion_engine.py`
- `gui/preview_canvas.py`

**Missing requested presets:**

- Float
- Shake
- Slide Left
- Slide Right
- Pulse
- Scale Up
- Scale Down
- Rotate Float

**Missing controls:**

- Animation Speed slider
- Animation Strength slider

---

## Medium Priority Bugs / Risks

### 9. Pipeline 4 overlay-only was previously freezing

**Status:** Recently patched but should be retested.

**Patch direction already applied:**

- Overlay-only graph uses original `0:v` base.
- `-shortest` is added when looped static text PNGs are introduced.

**Need validation:**

- Pipeline 4 with text only.
- Pipeline 4 with sticker only.
- Pipeline 4 with text + sticker.
- Pipeline 4 on videos with no audio.

---

### 10. Preview/export parity still needs visual QA

**Status:** Architectural path in place, not fully proven.

**Potential mismatch areas:**

- Qt preview canvas scaling vs final output canvas dimensions.
- Text antialiasing on Windows vs Linux.
- Sticker rotation bounding box vs FFmpeg rotate `rotw/roth`.
- Alpha fade / scale / pop motion.
- Timeline playhead active overlay visibility.

---

### 11. Image compositor input indexing is fragile

**Status:** Risk.

**File:** `core/pipeline/compositor_pipeline.py`

**Concern:**

- Image input index is derived from counting `graph.inputs` tokens after appending looped input args.
- This can become fragile as more input types are added.

**Fix direction:**

- Add a `FilterGraph.add_input(args: list[str]) -> int` helper that returns the new input index explicitly.

---

### 12. Text asset cache cleanup may conflict with reuse

**Status:** Risk.

**Files:**

- `core/overlays/text_engine.py`
- `core/renderer/batch_renderer.py`

**Concern:**

- `TextEngine` caches temp paths, while `BatchRenderer` cleans temp files after each video.
- If cache keeps deleted paths, it checks existence and regenerates, so it should work, but this should be tested.

---

## Suggested Immediate Test Matrix

1. Pipeline 1, with audio, image compositor enabled.
2. Pipeline 1, no audio, image compositor enabled.
3. Pipeline 2, with audio, image + text + sticker.
4. Pipeline 2, no audio, image + text + sticker.
5. Pipeline 3, with audio, text + sticker.
6. Pipeline 3, no audio, text + sticker.
7. Pipeline 4, with audio, text + sticker.
8. Pipeline 4, no audio, text + sticker.
9. Sticker Fade In / Fade Out / Pop / Bounce / Scale / Drift.
10. Text Fade In / Pop / Scale / multiline text.
11. Overlap fade at image height 20/35/60 and overlap 0/5/20.
12. Output path with videos from multiple source folders.

## Commands Useful for Debugging

```bash
python -m compileall core gui models utils main.py
```

```bash
rg "debug_filtergraph|debug_fade_filter|developer_mode" -n
```

```bash
rg "-map|original_audio|audio_label|c:a|probe" core/renderer core/pipeline utils -n
```

```bash
rg "MotionPreset|alpha_filter|region_scale_expr|eval=frame" core/overlays gui models -n
```

## Recently Addressed — Overlay Motion Patch 2026-05-09

The Fade/Pop/Scale motion bug has been partially addressed in code:

- `MotionPreset` now includes the requested common social motion presets.
- `MotionEngine` builds alpha fades and dynamic scale/position expressions for overlay regions.
- Text and sticker engines pass overlay start/end timing into dynamic region scaling.
- Preview canvas now applies matching alpha, scale, offset, and rotate-float helpers.

Remaining validation required:

- Run real FFmpeg renders for text/sticker Fade In, Fade Out, Pop, Scale, Pulse, Float, Shake, and slides.
- Confirm sticker Fade In preserves transparent PNG edges and does not disappear.
- Confirm preview/output parity visually on Windows.

## Recently Addressed — Realtime Motion Preview 2026-05-12

The preview/export split for motion has been addressed with a shared `core/motion_engine.py` module:

- `MotionSpec` stores timing, speed, strength, and preset.
- `PreviewTransformEvaluator` drives live preview opacity/scale/offset/rotation.
- `FFmpegExpressionBuilder` drives export expressions.
- Motion speed/strength values are stored on overlay models and passed to both preview and export.

Remaining validation required:

- Real GUI playback validation through Mini Timeline play/pause.
- Visual comparison between preview and rendered FFmpeg output.
- Real transparent sticker tests for Fade In/Fade Out and Rotate Float.

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

