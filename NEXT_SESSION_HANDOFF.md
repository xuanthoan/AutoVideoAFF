# AutoVideoAFF — Next Session Handoff

_Last updated: 2026-05-09_

This file is a compact handoff for the next development chat/session. It summarizes the current architecture, implemented modules, completed features, important code changes, and known remaining bugs/risks.

## 1. Product Goal

AutoVideoAFF is one unified PySide6 desktop application for mass-production social video workflows targeting TikTok, Instagram Reels, and YouTube Shorts.

Primary user flow:

1. Add many source videos to a queue.
2. Select one workflow mode.
3. Optionally shuffle visual scenes.
4. Optionally composite an image area with viewport fade.
5. Optionally add text/sticker overlays and timing.
6. Batch render final social-ready MP4 files.

Core rules that must be preserved:

- Do not split the product into multiple apps.
- Do not rebuild from scratch; continue improving the existing modules.
- Python handles GUI, state, planning, temp overlay assets, and FFmpeg orchestration.
- FFmpeg performs final video compositing/export.
- Keep one final encode per output video.
- Do not create intermediate H264/H265/MP4 stages.
- Keep overlays in normalized final-canvas coordinate space.
- Do not render full-frame RGBA overlays for every frame; use minimal overlay regions.

## 2. Current Repository Map

```text
main.py                         PySide6 app entry point.
models/                         Project, overlay, text, and sticker dataclasses.
core/pipeline/                  Pipeline modules and structured render graph primitives.
core/compositor/                Image layout, viewport fade, and compositor graph construction.
core/overlays/                  Template, typography, text, sticker, transform, and motion engines.
core/renderer/                  Batch renderer, FFmpeg command builder, preview frame extraction.
core/video/                     Scene detection, fallback segmentation, timestamp constants.
core/safe_area_engine.py        Normalized TikTok/Reels/Shorts safe-area calculations.
gui/                            Main window, queue panel, workflow panel, preview canvas, mini timeline.
utils/                          FFmpeg lookup/probing, file helpers, process lifecycle, logging.
assets/fonts/                   Intended bundled font location.
AutoVideoAFF.spec               PyInstaller one-dir packaging spec.
requirements.txt                PySide6 and PySceneDetect runtime dependencies.
```

## 3. Central State Model

`models/project_state.py` contains the main `ProjectState` passed from GUI to renderer.

Important fields:

- `videos`: batch input queue.
- `workflow_mode`: selected mutually exclusive pipeline mode.
- `scene_shuffle`: scene detection, fallback split, random/keep-first settings.
- `image_composite`: image pool, image height %, overlap %, crop focus, fade curve.
- `overlays`: text/sticker enabled flags, current overlay objects, multi-layer lists.
- `export`: output settings, CRF, preset, auto-open, developer mode.
- `safe_area`: internal platform/safe-area/snap settings.

Overlay coordinate contract:

- `OverlayBase.x` and `OverlayBase.y` are normalized final-canvas center ratios.
- `x=0.5`, `y=0.5` means the final output canvas center.
- Never store preview widget pixels as export coordinates.
- `StickerOverlay.scale` is a normalized canvas-width ratio, for example `0.16` means target sticker width is approximately `canvas_width * 0.16`.

## 4. Workflow Modes

The app currently supports four mutually exclusive modes:

| Mode | Name | Renderer modules |
| --- | --- | --- |
| `PIPELINE_1` | Shuffle + Image | scene shuffle, image compositor, final export |
| `PIPELINE_2` | Shuffle + Image + Overlay | scene shuffle, image compositor, overlay, final export |
| `PIPELINE_3` | Shuffle + Overlay | scene shuffle, overlay, final export |
| `PIPELINE_4` | Overlay Only | overlay, final export |

Notes:

- `gui/workflow_panel.py` owns UI locking via `PIPELINE_CONFIG`.
- `core/pipeline/manager.py` owns renderer-side module selection.
- Pipeline 4 must use the original input video as the overlay base and must not assume compositor/fade stage outputs exist.

## 5. Render Architecture

The renderer has moved toward a multi-stage logic pipeline while still producing one final FFmpeg command.

Key primitives in `core/pipeline/base.py`:

- `FilterNode`: named FFmpeg filter chain.
- `ShuffleSegment`: one visual segment time range.
- `ShufflePlan`: metadata for shuffled visual order.
- `LayoutPlan`: computed image/video/fade layout values.
- `FilterGraph`: mutable graph with inputs, nodes, labels, extra args, temp files, and debug events.
- `RenderJob`: input path, output path, state, optional original audio, video width, and video height.

Current intended stage order:

1. Shuffle plan: detect/split/shuffle visual segments only.
2. Layout plan: compute canvas/image/video/fade dimensions.
3. Image compositor plan: build image + shifted video + fade graph nodes.
4. Overlay plan: prepare text/sticker minimal region assets and overlay filters.
5. Final render: map final video, optional audio, codec args, and output path.

Do not turn these stages into intermediate MP4 exports. They are metadata/filtergraph stages only.

## 6. Scene Shuffle Stage

Implemented behavior:

- Uses PySceneDetect through `SceneDetector`.
- Falls back to random 3–5 second segments when scenes are insufficient.
- Keeps the first segment and shuffles the remaining segments.
- Builds video-only FFmpeg `trim,setpts` chains.
- Concats with `concat=n=...:v=1:a=0`.
- Stores `ShufflePlan` metadata/debug events.

Important rule:

- Audio must never be shuffled.
- Original audio should be extracted/restored only if the source video actually has audio.

## 7. Image Compositor and Viewport Fade

Implemented behavior:

- Dynamic image height percent, default 35%, range 20–60%.
- Dynamic overlap percent, default 5%, clamped to `0..min(20, image_height_percent)`.
- Crop focus: top, center, bottom.
- Numeric canvas size generated from probed source video dimensions.
- Zero-overlap path bypasses fade generation.

Current layout formulas:

```text
W = canvas width
H = canvas height
image_h = H * image_height_percent / 100
overlap_h = H * overlap_percent / 100
visible_video_total = H - (image_h - overlap_h)
offset_y = -(H - visible_video_total)
main_video_h = visible_video_total - overlap_h
image_top = H - image_h
fade_start = image_top
source_y = fade_start - offset_y
```

Layer order must remain:

1. base canvas
2. image layer
3. main video region
4. alpha fade strip from the viewport overlap region
5. text overlays
6. sticker overlays

Recent fix:

- The opaque main video region is cropped before overlap so it does not hide the alpha fade strip.

Remaining risk:

- Needs real-media verification for 720x1280 and 1080x1920 videos.
- `fade_curve` exists but current implementation appears mostly linear.

## 8. Overlay System

Overlay architecture:

- Text and stickers are final post-composition overlays.
- They are positioned in final-canvas normalized coordinates.
- They should never be attached to raw source video pixels before viewport shift.

Text overlay:

- Raw FFmpeg `drawtext` was removed for final social typography.
- Text is rendered with Qt/QPainter into minimal transparent RGBA PNG regions.
- The generated text PNG is overlaid onto the final canvas by FFmpeg.
- Text asset cache avoids re-rendering identical static text regions during command construction.
- Background boxes are flat rounded rectangles; outer/drop shadow on the box was removed.

Sticker overlay:

- Sticker input is scaled by final canvas width, not preview pixels or source sticker size.
- Rotation uses FFmpeg `rotate=...:c=none`.
- Sticker positioning uses the same normalized final-canvas transform model as text.

Important performance rule:

- Do not generate full-frame RGBA overlay frames.
- Render only text bounding boxes, sticker regions, or minimal animated overlay regions.

## 9. Motion / Animation System

Current code contains a shared `MotionEngine` with helper methods for:

- position expressions;
- alpha filters;
- dynamic region scale expressions;
- preview alpha;
- preview scale;
- sticker canvas-width scale.

Current known broken/incomplete behavior:

- Text Fade motion may not work.
- Sticker Fade In can make sticker disappear.
- Pop may be too subtle or have no visible effect.
- Text Scale may not animate correctly.
- Preview/export parity for motion is not proven.

Required next direction:

- Apply motion after immutable overlay asset creation, before final overlay composite.
- Fade must multiply original alpha by motion alpha; do not overwrite PNG alpha to zero.
- Dynamic scale/position/rotation must use FFmpeg expressions evaluated per frame.
- Preview must use the same easing/timing formulas as export.
- Add/complete popular presets: Fade, Pop, Bounce, Float, Slide Left/Right/Up/Down, Pulse, Shake, Scale Up/Down, Rotate Float.
- Add optional Animation Speed and Animation Strength controls later if needed.

## 10. GUI Architecture

Current GUI layout:

```text
Left column:    video queue + queue buttons + log panel
Center column:  preview canvas + mini timeline
Right column:   scrollable workflow controls + fixed render/stop/open controls
```

Implemented GUI pieces:

- `MainWindow`: app shell, state synchronization, render worker wiring, preview/timeline sync.
- `QueuePanel`: add files, add folder, remove selected, clear queue, selection preview.
- `WorkflowPanel`: pipeline selection and compact workflow controls.
- `PreviewCanvas`: thumbnail preview, safe area, overlay preview, drag/snap, live overlay repaint.
- `MiniTimeline`: lightweight overlay timing layer.
- Fixed render, stop, and open-output buttons remain visible outside the workflow scroll area.

Safe area/snap:

- Dedicated Safe Area/Snap panel was removed from the GUI.
- Safe area and snapping remain enabled internally by default.
- Safe area calculations apply to final canvas space.

## 11. Mini Timeline

Implemented behavior:

- Compact timeline below preview.
- Overlay blocks for text and stickers.
- Playhead, play/pause/stop controls.
- Drag timing and resize duration.
- Visibility toggles.
- Selected block highlight.
- Preview only shows overlays active at current playhead time.

Important rule:

- Timeline is only an overlay timing UI layer.
- It must not become a full NLE timeline with video/audio track editing.
- Final render still uses FFmpeg overlay timing expressions such as `enable='between(t,start,end)'`.

## 12. Output and Process Handling

Output routing:

- Output folder is beside the first queued video, not inside the project folder.
- Example: `D:/CampaignA/video1.mp4` -> `D:/CampaignA/output/video1.mp4`.
- If inputs come from multiple folders, the first queued video determines output root.

Output safety:

- Safe naming avoids overwriting existing files.
- Render writes to a hidden `.rendering.mp4` first.
- Output is verified by ffprobe before final rename.

Process handling:

- `ProcessManager` wraps FFmpeg subprocess execution.
- Stop should kill the active FFmpeg process and stop remaining queue work.
- One failed video should be logged/skipped without crashing the full batch.

Developer mode:

- `ExportSettings.developer_mode` defaults to `False`.
- Debug files such as `debug_filtergraph.txt` and `debug_fade_filter.txt` should only be written when developer mode is enabled.
- Release/default renders should export only the final video and required temp files should be cleaned.

## 13. Completed Features Summary

Current implemented/scaffolded features:

- PySide6 desktop app scaffold.
- Three-column production layout.
- Queue add/remove/clear and selected video preview.
- Realtime first-frame preview using FFmpeg at `-ss 0.05`.
- Four workflow modes with pipeline-dependent UI locking.
- Scene shuffle planning with PySceneDetect and fallback segmentation.
- Video-only shuffle filtergraph; audio intended to be restored separately.
- Dynamic image compositor settings.
- Viewport overlap fade graph with computed layout plan.
- Final-canvas normalized text/sticker overlay architecture.
- Qt/QPainter minimal text region rendering.
- Sticker canvas-width-relative scale logic.
- Template system with built-in templates and Random Template selection.
- Mini timeline overlay timing UI.
- Safe area and snapping in preview.
- Batch render loop with progress logs and stop hook.
- Output folder beside first input video.
- PyInstaller spec and basic font-bundling notes.
- Internal docs: `ARCHITECTURE.md`, `RENDER_PIPELINE.md`, `ANIMATION_SYSTEM.md`, `FFmpeg_PIPELINE.md`, `PROJECT_STATUS.md`, `BUGS.md`.

## 14. Critical Bugs / Risks Still Open

### 14.1 No-audio input can hang/fail

Status: critical / not fully fixed.

Problem:

- Pipeline can still assume extracted audio exists.
- Command builder does not have explicit `has_audio` handling.
- `FFmpegBuilder.output_args()` still unconditionally includes `-c:a aac`.

Required fix:

1. Add `probe_has_audio(path: Path) -> bool` using ffprobe stream detection.
2. Add `has_audio` to `RenderJob` or pass it into `FFmpegBuilder.build()`.
3. If audio exists and extraction succeeds:
   - add extracted audio input;
   - map that audio input;
   - add `-c:a aac`.
4. If no audio exists:
   - do not create fake/empty audio;
   - do not add audio input;
   - do not map audio;
   - do not add `-c:a`.
5. Add command construction tests for audio and no-audio cases.

### 14.2 Overlay animation engine incomplete/broken

Status: critical / not fully fixed.

Symptoms:

- Text Fade does not work.
- Sticker Fade In can disappear.
- Pop is not visibly working.
- Text Scale does not animate correctly.

Required fix:

- Introduce/complete unified overlay animation model.
- Preserve source alpha for PNG/sticker assets.
- Use per-frame FFmpeg expressions for scale/position/rotation.
- Make preview and output use identical formulas.
- Add tests for generated FFmpeg expressions.

### 14.3 Fade overlap requires real media QA

Status: recently patched / needs validation.

Verify:

- Fade is visible.
- Fade is the actual shifted video region overlapping the image.
- No jump frame or visual discontinuity around overlap.
- Works for 720x1280 and 1080x1920.
- Works with image height 20/35/60 and overlap 0/5/20.

### 14.4 Pipeline 4 overlay-only requires retest

Status: patched but not fully proven.

Verify:

- Text only.
- Sticker only.
- Text + sticker.
- With audio.
- Without audio.
- Stop button during overlay-only render.

### 14.5 Font parity incomplete

Status: incomplete until real font files are bundled.

Risk:

- If Montserrat/Poppins are missing, Qt may use platform fallback fonts.
- Preview/export may differ between machines.

Required fix:

- Add licensed Montserrat ExtraBold/Poppins ExtraBold files to `assets/fonts/`.
- Ensure `SocialTypographyRenderer` explicitly loads bundled font files.
- Test on clean Windows machine.

### 14.6 Template color conflict

Status: product decision needed.

Conflict:

- Earlier requirement: `Orange White` background `#F57C4D`.
- Later typography requirement: orange visual tone approximately `#F58B57`.

Next step:

- Decide whether exact template definitions or latest visual tone has priority.

### 14.7 Input indexing is fragile

Status: risk.

Problem:

- Some graph input indexes are derived by counting `-i` tokens in `graph.inputs`.
- This can break as more input types are added.

Suggested fix:

- Add `FilterGraph.add_input(args: list[str]) -> int` that returns the exact FFmpeg input index.

## 15. Suggested Next Work Order

1. Fix optional audio detection and dynamic FFmpeg audio command building.
2. Fix overlay animation engine for Fade/Pop/Scale/Bounce/Slide and preview-output parity.
3. Retest Pipeline 4 overlay-only with audio and no-audio videos.
4. Verify image compositor/fade on real 720x1280 and 1080x1920 videos.
5. Add unit tests for FFmpeg command construction.
6. Add small sample-media integration tests if feasible.
7. Bundle actual font files and test clean Windows environment.
8. Verify default release render creates no debug artifacts.
9. Refactor input indexing with explicit `FilterGraph.add_input()`.
10. Decide template color source of truth.

## 16. Useful Debug Commands

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

```bash
rg "output_directory_for_videos|safe_output_path|temporary_output_path" -n
```

## 17. Instructions for Future Development Sessions

Use these rules when continuing work:

- Do not rebuild the entire app.
- Do not remove the existing PySide6 GUI or workflow mode system.
- Do not replace FFmpeg with MoviePy/OpenCV final rendering.
- Do not add intermediate MP4 encode stages.
- Keep final output as one final encode.
- Keep audio optional and independent from visual filtergraph stages.
- Keep overlays as final-canvas normalized post-composition elements.
- Keep text typography rendered as minimal Qt/QPainter RGBA regions.
- Keep sticker scaling canvas-relative.
- Keep safe area/snap internal defaults enabled.
- Keep output path as first input folder plus `/output`.
- Add tests whenever changing FFmpeg command construction, image fade math, or motion expressions.

## 18. Motion Patch Update — 2026-05-09

A first pass of the overlay animation fix has been applied:

- More social motion presets were added to `MotionPreset` and GUI dropdowns.
- `MotionEngine` now centralizes FFmpeg and preview motion formulas.
- Text and sticker engines apply dynamic scale/alpha/position after immutable asset creation.
- Preview canvas now applies matching alpha, scale, offset, and rotate-float helpers.

Still required in the next session:

- Real render validation for every motion preset.
- Visual preview/output parity checks.
- Optional no-audio command fix remains critical and should be tackled next.

## 19. Realtime Motion Preview Update — 2026-05-12

A realtime preview/export motion parity pass has been added:

- New `core/motion_engine.py` owns `MotionSpec`, numeric preview evaluation, and FFmpeg expression generation.
- `core/overlays/motion_engine.py` is now only a compatibility wrapper.
- Preview canvas evaluates motion on the current playhead timestamp and emits throttled `[PREVIEW_MOTION]` logs.
- Text/sticker speed and strength controls affect both preview and export.
- Region-only RGBA overlay pipeline remains unchanged.

Next work: validate real GUI playback and rendered output, then fix optional no-audio rendering.

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

