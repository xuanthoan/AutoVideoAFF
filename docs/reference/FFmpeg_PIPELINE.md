# AutoVideoAFF FFmpeg Pipeline Reference

_Last updated: 2026-05-08_

This document records how FFmpeg commands are assembled, how inputs/maps/filter labels are expected to work, and what must be fixed or preserved in future development.

## 1. FFmpeg/FFprobe Discovery

`utils/ffmpeg_helper.py` resolves executables in this order:

1. bundled `bin/ffmpeg.exe` / `bin/ffprobe.exe` under app root;
2. executable in app root;
3. current working directory equivalents;
4. system `PATH`.

If required binaries are missing, `FFmpegNotFoundError` is raised with a Vietnamese user-actionable message.

## 2. Probing

Current helper functions:

- `probe_duration(path)`: uses FFprobe `format=duration`.
- `probe_video_size(path)`: uses FFprobe `stream=width,height` for `v:0`.

Known missing helper:

- `has_audio_stream(path)` should be added for no-audio-safe rendering.

Suggested FFprobe command for audio detection:

```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of json input.mp4
```

If no audio streams are returned, the final command must not add audio input, audio map, or audio codec args.

## 3. Command Builder Overview

`FFmpegBuilder.build(job, graph)` currently starts commands as:

```text
ffmpeg -y -i <input_video> <graph.inputs...>
```

Then, if `job.original_audio_path` exists, it appends:

```text
-i <original_audio_path>
```

Then it emits filter/map args:

- if graph has chains:
  - `-filter_complex <graph.filter_complex()>`
  - `-map [<graph.video_label>]`
  - optional audio map based on `graph.audio_label`
- if graph has no chains:
  - `-map 0:v -map 0:a?`

Finally it appends `graph.extra_args` and output path.

## 4. Input Indexing Contract

Base input:

```text
0 = source video
```

Additional inputs are appended by graph modules in order:

- Image compositor: looped image input.
- Text overlay: looped generated PNG region inputs.
- Sticker overlay: sticker image inputs.
- Original audio: appended by `FFmpegBuilder` after graph inputs if `job.original_audio_path` is present.

Important: hardcoded audio indexes are fragile. The builder calculates `original_audio_index` as:

```python
1 + sum(1 for token in graph.inputs if token == "-i")
```

Future changes should preserve dynamic index calculation or replace it with a more explicit input registry.

## 5. FilterGraph Output Mapping

When `graph.chains` exists:

```text
-filter_complex <chains joined by semicolon>
-map [graph.video_label]
```

Audio mapping rules currently:

- `graph.audio_label == "original_audio"` and audio input exists:
  - map `<original_audio_index>:a:0`
- other `graph.audio_label` value:
  - if it ends with `?`, map `0:a?`
  - otherwise map `[graph.audio_label]`

Known issue: output args still include `-c:a aac` unconditionally even when no audio is mapped.

## 6. Current Output Codec Args

`FFmpegBuilder.output_args(settings)` currently returns:

```text
-c:v libx264
-preset <preset>
-crf <crf>
-pix_fmt yuv420p
-c:a aac
-movflags +faststart
```

This is acceptable for audio outputs but should become conditional for no-audio videos.

Recommended future interface:

```python
build_ffmpeg_command(has_audio: bool)
# or
FFmpegBuilder.output_args(settings, has_audio: bool)
```

If `has_audio == False`, omit:

- audio input;
- audio map;
- `-c:a aac`;
- any fake/silent audio generation.

## 7. Timestamp and Duration Args

Current shuffle pipeline appends:

```text
-fps_mode passthrough
-fflags +genpts
-shortest
```

Rationale:

- `-fps_mode passthrough` replaced deprecated `-vsync 2`.
- `-fflags +genpts` helps regenerate stable timestamps.
- `-shortest` prevents looped static overlay PNG inputs from keeping the output alive forever.

Be careful with `-shortest`: it is necessary when `-loop 1` PNG inputs exist but can also interact with audio duration. Test both audio and no-audio inputs.

## 8. Shuffle Filter Shape

For video-only shuffle:

```text
[0:v]trim=start=0.000:end=4.000,setpts=PTS-STARTPTS[shv0];
[0:v]trim=start=8.000:end=12.000,setpts=PTS-STARTPTS[shv1];
[shv0][shv1]concat=n=2:v=1:a=0[shuffled_v]
```

No `atrim` should be generated for shuffled segments. Original audio timeline should remain external.

## 9. Image Compositor Filter Shape

For image compositor with overlap:

```text
[image]scale=w=W:h=-1,crop=w=W:h=image_h:x=(iw-W)/2:y=<focus>[bg];
color=c=black@0:s=WxH:d=1[canvas];
[canvas][bg]overlay=x=0:y=image_top[base];
[video]setpts=PTS-STARTPTS,split=2[main_src][fade_src];
[main_src]crop=w=W:h=main_video_h:x=0:y=-offset_y[mainv];
[fade_src]crop=w=W:h=overlap_h:x=0:y=source_y,format=yuva420p,geq=lum='p(X,Y)':a='255*(1-(Y/overlap_h))'[fade];
[base][mainv]overlay=x=0:y=0[main_layer];
[main_layer][fade]overlay=x=0:y=fade_start[composited_v]
```

Important rules:

- numeric `W` and `H` must be injected by Python;
- never emit literal `WxH` in `color=s=`;
- precompute `overlap_h` in Python;
- skip fade graph if `overlap_h <= 0`;
- fade is the viewport overlap region, not raw source video bottom.

## 10. Text Overlay Filter Shape

Text is not drawn by FFmpeg `drawtext`. It is a Qt-rendered minimal PNG region.

Current filter shape:

```text
[text_png]scale=w='<region_scale_expr>':h='<height_expr>':eval=frame,<alpha_filter>[text_src];
[current_video][text_src]overlay=x=W*x_ratio-w/2:y=H*y_ratio-h/2:enable='between(t,start,end)'[text_v]
```

Text PNG inputs are added with:

```text
-loop 1 -i text_region.png
```

Because looped static PNG inputs can be infinite, `-shortest` must be present.

## 11. Sticker Overlay Filter Shape

Current filter shape:

```text
[sticker]
  scale=w='<canvas_width * scale_ratio * motion_expr>':h='-1':eval=frame,
  rotate=<rotation>*PI/180:ow=rotw(iw):oh=roth(ih):c=none,
  <alpha_filter>
[sticker_src];
[current_video][sticker_src]overlay=x=W*x_ratio-w/2:y=H*y_ratio-h/2:enable='between(t,start,end)'[sticker_v]
```

Sticker scale must remain canvas-relative, not source-image-relative.

## 12. Developer Mode Debug Files

Current batch renderer only calls debug-file writers if `render_state.export.developer_mode` is true.

Debug files:

- `debug_filtergraph.txt`: full filtergraph.
- `debug_fade_filter.txt`: fade-relevant chains only.

Release/default mode must not create these files.

## 13. Logs

Renderer logs include timestamps and levels:

```text
[HH:MM:SS] [INFO] ...
[HH:MM:SS] [WARNING] ...
[HH:MM:SS] [ERROR] ...
[HH:MM:SS] [SUCCESS] ...
```

Current renderer logs FFmpeg command lines. It only logs FFmpeg stderr tails on failure, not frame-by-frame spam on success.

## 14. Critical No-Audio Fix Plan

The current code has a known no-audio risk. The correct behavior should be:

### Mode A — source has audio

```text
1. detect audio stream
2. extract original audio to temp m4a/aac
3. render video pipeline video-only
4. add original audio as final input
5. map final video + original audio
6. encode video + AAC audio
```

### Mode B — source has no audio

```text
1. detect no audio stream
2. skip audio extraction
3. render video pipeline video-only
4. do not add audio input
5. do not map audio
6. do not emit -c:a aac
```

Do not use:

- `anullsrc`;
- fake silent track;
- empty `.m4a`;
- hardcoded `-map 2:a:0`.

Recommended code changes:

1. Add `has_audio_stream(path)` in `utils/ffmpeg_helper.py`.
2. Have `BatchRenderer` call it before extraction.
3. If no audio, set `original_audio_path = None` and mark graph/builder as no-audio.
4. Make output args conditional on mapped audio.
5. Add tests for both audio and silent video command generation.

## 15. FFmpeg Change Checklist

Before committing FFmpeg changes:

- inspect generated command for each pipeline mode;
- ensure input indexes are correct after image/text/sticker/audio inputs;
- test no-image/no-overlay pipeline paths;
- test Pipeline 4 overlay-only path;
- test source with audio and source without audio;
- confirm no intermediate MP4 encodes;
- confirm `debug_*.txt` files only appear in developer mode;
- run `python -m compileall core gui models utils main.py`;
- add focused Python assertions for generated filtergraph strings.

## 2026-05-09 Overlay Motion Filter Notes

Overlay motion filters now follow this shape:

```text
[overlay_input]
scale=w='<dynamic_width>':h='<dynamic_height>':eval=frame,
format=rgba,
fade=t=in|out:st=<time>:d=<duration>:alpha=1
[prepared_overlay]

[base][prepared_overlay]
overlay=x=<dynamic_x>:y=<dynamic_y>:enable='between(t,start,end)'
[out]
```

Sticker overlays may also include dynamic `rotate='<expr>'` before alpha preparation.

Important:

- Keep `eval=frame` for dynamic scale expressions.
- Keep overlays as minimal regions, not full-frame sequences.
- Escape expression commas when embedding `if()`, `min()`, or `max()` expressions inside FFmpeg filter options.

## 2026-05-12 Motion Expression Source of Truth

FFmpeg overlay animation expressions are now generated by `core/motion_engine.py` through `FFmpegExpressionBuilder`.

Important command-generation rules:

- Dynamic region scale continues to use `scale=w='<expr>':h='<expr>':eval=frame`.
- Fade continues to use RGBA alpha filters on overlay regions.
- Rotate Float generates a dynamic `rotate='<expr>'` for stickers.
- Speed and strength must be included in generated expressions when overlay settings differ from defaults.

Do not duplicate these expressions in text/sticker engines; call the shared builder.

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

