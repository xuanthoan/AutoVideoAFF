# AutoVideoAFF Render Pipeline Internals

_Last updated: 2026-05-08_

This document explains how the current multi-stage logic pipeline produces one final FFmpeg command and one final encode. Read this before changing scene shuffle, image compositing, overlay ordering, output paths, or batch behavior.

## 1. Pipeline Design Summary

The renderer is a metadata/filtergraph pipeline, not a sequence of encoded video files.

```text
ProjectState
  -> BatchRenderer
  -> PipelineManager
  -> RenderJob + FilterGraph
  -> SceneShufflePipeline       (optional)
  -> ImageCompositePipeline     (optional)
  -> OverlayPipeline            (optional)
  -> FinalExportPipeline
  -> FFmpegBuilder
  -> one FFmpeg process / one final encoded MP4
```

Pipeline stages may create non-video temporary assets such as typography PNG regions, but they must not create intermediate MP4/H264/H265 renders.

## 2. Batch Render Lifecycle

`BatchRenderer.render(state, progress, log)` owns queue processing.

For every video:

1. Resolve output folder using the first queued video.
2. Generate a safe non-overwriting final path.
3. Generate hidden temporary `.rendering.mp4` path.
4. Remove stale temp output/audio files.
5. Optionally extract original audio for shuffle workflows.
6. Deep-copy state if `Random Template` needs per-video template replacement.
7. Build a final FFmpeg command through `PipelineManager`.
8. Optionally write debug filter files if developer mode is enabled.
9. Run FFmpeg through `ProcessManager`.
10. Verify temp output with FFprobe.
11. Rename temp output to final output.
12. Verify final output.
13. Clean temporary overlay/audio files.

One video failure is logged and skipped; batch rendering continues unless the user presses Stop.

## 3. RenderJob

`RenderJob` contains:

- `input_path`: source video.
- `output_path`: temp render output path for the current run.
- `state`: render state for this video.
- `original_audio_path`: optional extracted original audio.
- `video_width`, `video_height`: probed from the source video.

The canvas currently follows the source video dimensions as probed by FFprobe. Most target workflows are 9:16 vertical videos.

## 4. FilterGraph Contract

`FilterGraph` is mutated by pipeline modules. Important fields:

- `inputs`: extra FFmpeg input tokens after `-i input.mp4`, such as `-loop 1 -i text.png`.
- `nodes`: ordered filter chains.
- `video_label`: current video output label after each module.
- `audio_label`: optional audio mapping label/convention.
- `extra_args`: final command args such as timestamp flags, `-shortest`, codecs.
- `temp_files`: temporary assets to clean.
- `shuffle_plan`: optional segment metadata.
- `layout_plan`: optional image/fade layout metadata.
- `debug_events`: human-readable pipeline events for logs.

A module must read `graph.video_label` as its input and set a new output label when it changes the video stream.

## 5. Stage 1 — Shuffle Plan and Video-Only Shuffle

### Responsibility

`SceneShufflePipeline`:

- runs PySceneDetect via `SceneDetector`;
- falls back to `Segmenter` if needed;
- keeps first segment and shuffles remaining segments;
- records a `ShufflePlan`;
- builds video-only trim/concat nodes.

### Filter shape

For segments `[A, B, C]`, output is conceptually:

```text
[0:v]trim=start=A.start:end=A.end,setpts=PTS-STARTPTS[shv0]
[0:v]trim=start=B.start:end=B.end,setpts=PTS-STARTPTS[shv1]
[0:v]trim=start=C.start:end=C.end,setpts=PTS-STARTPTS[shv2]
[shv0][shv1][shv2]concat=n=3:v=1:a=0[shuffled_v]
```

### Audio rule

Audio must never be shuffled. Shuffle output is video-only. Original audio should be remuxed separately if it exists.

### Known follow-up

Current no-audio behavior must be audited/fixed so final commands do not assume an extracted `.m4a` exists.

## 6. Stage 2 — Layout Plan

`ImageCompositor.build_plan()` computes dynamic layout values from `ImageCompositeSettings`, `video_width`, and `video_height`.

Definitions:

```text
W = canvas width
H = canvas height
IH = clamped image_height_percent, 20..60
OV = clamped overlap_percent, 0..min(20, IH)

image_h             = even_pixels(H * IH / 100)
overlap_h           = even_pixels(H * OV / 100)
visible_video_total = H - (image_h - overlap_h)
offset_y            = -(H - visible_video_total)
main_video_h        = visible_video_total - overlap_h
image_top           = H - image_h
fade_start          = image_top
source_y            = fade_start - offset_y, clamped for crop safety
```

The plan exists to keep layout math out of procedural string concatenation.

## 7. Stage 3 — Image Compositor and Viewport Fade

### Correct layer order

```text
1. base canvas
2. processed image layer at image_top
3. main visible video region
4. alpha fade strip from viewport overlap region
```

### Image processing

The image layer uses:

```text
scale=w=W:h=-1
crop=w=W:h=image_h:x=(iw-W)/2:y=<focus>
```

Focus values:

- `top`: `0`
- `center`: `(ih-oh)/2`
- `bottom`: `ih-oh`

### Fade logic

Fade must be the video region that overlaps the image after viewport offset.

Current graph structure when `overlap_h > 0`:

```text
[video]setpts=PTS-STARTPTS,split=2[main_src][fade_src]
[main_src]crop=w=W:h=main_video_h:x=0:y=-offset_y[mainv]
[fade_src]crop=w=W:h=overlap_h:x=0:y=source_y,format=yuva420p,geq=...[fade]
[base][mainv]overlay=x=0:y=0[main_layer]
[main_layer][fade]overlay=x=0:y=fade_start[composited_v]
```

The fade strip must sit above the image/base composition. If the opaque main video also covers the overlap region, the fade will be hidden. This is why `main_video_h` is cropped separately.

### Zero-overlap mode

If `overlap_h <= 0`, the fade stage is skipped entirely to avoid invalid crop height and unnecessary graph complexity.

## 8. Stage 4 — Overlay Plan

Overlay stage is final-canvas post-composition.

### Text overlays

1. `TextEngine.render_asset()` renders text into a minimal transparent PNG region.
2. The PNG is added as `-loop 1 -i text_region.png`.
3. `TextEngine.build_filter()` applies motion scale/alpha and overlays onto current final canvas label.

### Sticker overlays

1. Sticker image is added as an input.
2. `StickerEngine.build_filter()` scales by normalized canvas width, rotates, applies alpha/motion, and overlays onto current final canvas label.

### Overlay ordering

Current ordering is:

1. all active text overlays;
2. all active sticker overlays.

If visual z-order needs more control later, introduce explicit layer ordering in models rather than changing this implicitly.

## 9. Stage 5 — Final Export

`FinalExportPipeline` appends codec settings through `FFmpegBuilder.output_args()`.

Current default output args:

```text
-c:v libx264
-preset <state.export.preset>
-crf <state.export.crf>
-pix_fmt yuv420p
-c:a aac
-movflags +faststart
```

Important caveat: `-c:a aac` is currently unconditional in output args. For no-audio input, future code should omit audio codec args when no audio is mapped.

## 10. Pipeline Mode Behavior

| Mode | Base video entering overlay stage | Image/fade? | Overlay? |
| --- | --- | --- | --- |
| Pipeline 1 | shuffled video | yes | no |
| Pipeline 2 | image-composited shuffled video | yes | yes |
| Pipeline 3 | shuffled video | no | yes |
| Pipeline 4 | original input video | no | yes |

Pipeline 4 must never assume `composited_v`, image inputs, or fade labels exist.

## 11. Temporary Files

Allowed temporary files:

- `.rendering.mp4` final output staging file.
- extracted `.rendering.m4a` if source has audio and shuffle needs original audio restoration.
- minimal text-region PNG assets.

Disallowed temporary files:

- intermediate video-stage MP4s;
- full-frame RGBA overlay sequences;
- debug text files in release mode;
- fake/silent audio tracks for no-audio inputs.

## 12. Debug Events

Graph stages currently append events like:

```text
[SHUFFLE] segment_count=... order=...
[LAYOUT] image_h=... overlap_h=... offset_y=... fade_start=... source_y=...
[FADE] image_h=... overlap_h=... visible_video_total=... fade_overlay_y=...
[OVERLAY] text index=... asset=... region=minimal_bbox
[OVERLAY] sticker index=... target_width=... center=(x,y) rotation=...
[FINAL] node_count=... resolution=... output=...
```

These are log events, not required debug files.

## 13. Output Directory Rules

The batch output directory is:

```text
first_video.parent / "output"
```

`safe_output_path()` avoids overwrites:

```text
video.mp4
video_001.mp4
video_002.mp4
```

## 14. Renderer Change Checklist

Before modifying renderer logic, verify:

- active pipeline modes still select the correct modules;
- graph labels are valid after each module;
- no stage assumes an optional previous stage exists;
- text/sticker overlay happens after image/fade composition;
- no intermediate video encode is introduced;
- no full-frame overlay sequence is introduced;
- no-audio inputs are handled without audio inputs/maps/codecs;
- output folder remains first-input-folder/output;
- `python -m compileall core gui models utils main.py` passes;
- filter-string unit checks cover new graph behavior.

## 16. Overlay Motion Stage Update — 2026-05-09

Overlay motion is now explicitly part of the overlay stage, after text/sticker asset creation and before final overlay compositing.

Expected filter order for each overlay region:

1. Load or render immutable RGBA region.
2. Scale dynamically with `eval=frame` when motion requires it.
3. Rotate dynamically for sticker rotate-float when requested.
4. Apply RGBA alpha fade if requested.
5. Overlay onto the current final-canvas label with timing `enable='between(t,start,end)'`.

This keeps motion lightweight and avoids full-frame RGBA animation sequences.

## 17. Realtime Motion Preview / Export Parity — 2026-05-12

Motion transform generation is now shared between preview and export through `core/motion_engine.py`.

Preview path:

1. Mini Timeline advances the playhead timestamp.
2. Preview canvas requests a `PreviewTransform` for each visible overlay.
3. The canvas applies opacity, scale, x/y offset, and rotation delta to the region pixmap.

Export path:

1. Text/sticker engines pass the same preset, start/end, speed, and strength into `FFmpegExpressionBuilder`.
2. The builder generates dynamic FFmpeg expressions.
3. FFmpeg composites the transformed region onto the final canvas.

No full-frame overlay stage is introduced.

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

