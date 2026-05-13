# AutoVideoAFF Animation and Overlay System

_Last updated: 2026-05-08_

This document describes the current text/sticker overlay architecture, motion model, preview/export parity contract, and known animation risks.

## 1. Design Goal

The overlay system must support high-quality social typography and sticker motion without rendering full-frame RGBA overlays. It should animate minimal overlay regions on top of the final video canvas.

Core requirements:

- text/sticker overlays are final post-composition overlays;
- overlay coordinates are normalized final-canvas ratios;
- text rendering uses Qt/QPainter for preview/export parity;
- sticker scale is canvas-relative;
- motion is applied after overlay asset creation;
- no recursive preview framebuffer rendering;
- no full-frame PNG sequences unless explicitly introduced in a future architecture discussion.

## 2. Data Model

### `OverlayBase`

Base fields:

- `enabled`
- `x`, `y`: normalized final-canvas center coordinates.
- `start_time`, `end_time`, `duration`: mini-timeline timing range.
- `motion`: `MotionPreset` enum.

Helpers:

- `set_timing(start, end)` clamps duration to at least 0.1s.
- `set_full_duration(video_duration)` defaults overlay to entire video.
- `active_at(current_time)` is used by preview/timeline logic.

### `TextOverlay`

Adds:

- `text`
- `template`
- `font_size`

Active when enabled and text is non-empty.

### `StickerOverlay`

Adds:

- `path`
- `scale`: normalized canvas-width ratio.
- `rotation`: degrees.

Active when enabled and a path exists.

## 3. Supported MotionPreset Values

Current enum values:

- `None`
- `Fade In`
- `Fade Out`
- `Bounce`
- `Pop`
- `Slide Up`
- `Slide Down`
- `Scale`
- `Drift`
- backward-compatible aliases: `Fade`, `Slide`, `Zoom`, `Elastic`

The GUI currently exposes a smaller subset depending on text/sticker panel:

- text: `None`, `Fade`, `Slide`, `Bounce`, `Pop`, `Scale`, `Drift`
- sticker: `None`, `Fade In`, `Fade Out`, `Bounce`, `Pop`, `Slide Up`, `Slide Down`

Requested but not fully modeled yet: `Float`, `Shake`, `Pulse`, `Slide Left`, `Slide Right`, `Rotate Float`, speed slider, strength slider.

## 4. Shared Transform Model

`core/overlays/transform.py` defines `OverlayTransform`.

It normalizes/clamps:

- center `x`, `y`;
- sticker `scale_ratio`;
- rotation;
- motion;
- timing.

Important helpers:

```text
center_pixels(canvas_width, canvas_height) -> (x_px, y_px)
sticker_width_pixels(canvas_width) -> round(canvas_width * scale_ratio)
```

Preview and export should use equivalent math.

## 5. Typography Rendering

### Visual master

Preview typography is intended to be the visual master. Export text should be generated using the same renderer rather than FFmpeg `drawtext`.

### Renderer

`SocialTypographyRenderer` uses Qt/QPainter to render text into a minimal transparent PNG region.

Key properties:

- no raw FFmpeg `drawtext` for final social text;
- minimal bounding-box region, not full canvas;
- bundled font preference: `Montserrat-ExtraBold.ttf`, then `Poppins-ExtraBold.ttf`;
- fallback font family names if bundled files are missing;
- anti-aliased rounded background box;
- no background box shadow in current implementation;
- text color and box color come from `TemplateManager`.

### Style constants

Current `TypographyStyle` defaults:

```text
line_spacing_ratio        = 0.32
horizontal_padding_ratio  = 0.95
vertical_padding_ratio    = 0.58
border_radius_ratio       = 0.42
shadow_opacity            = 0.22  # currently not used for box shadow
max_width_ratio           = 0.74
```

Note: `shadow_opacity` remains in the dataclass but the current renderer does not draw a background box shadow.

## 6. Template System

`TemplateManager` contains built-in templates plus `Random Template` behavior.

Current built-ins:

| Name | Text | Background |
| --- | --- | --- |
| Orange White | `#FFFFFF` | `#F58B57` |
| White Black | `#000000` | `#FFFFFF` |
| Pink White | `#FFFFFF` | `#FF3FA4` |
| Red White | `#FFFFFF` | `#FF4B4B` |
| Yellow White | `#FFFFFF` | `#EFCB39` |
| Pastel Pink | `#F0537A` | `#FFD7DF` |
| Green White | `#FFFFFF` | `#8BC34A` |

Important historical note: earlier user specs requested Orange White background `#F57C4D`; later typography tuning changed it to `#F58B57`. Treat this as a known product/design decision to clarify before enforcing exact template tests.

## 7. Text Export Flow

For each active text overlay:

1. `TextEngine.render_asset()` generates or reuses a cached PNG region.
2. `OverlayPipeline` adds `-loop 1 -i <text_region.png>` to graph inputs.
3. `TextEngine.build_filter()` emits:
   - dynamic `scale` with `eval=frame`;
   - `format=rgba` or `fade=...:alpha=1` via `MotionEngine.alpha_filter()`;
   - final `overlay=x=...:y=...:enable='between(...)'`.
4. The new video label becomes `text_v_<index>`.

Current text filter shape:

```text
[text_input]scale=w='<expr>':h='<expr>':eval=frame,<alpha>[text_src]
[current_video][text_src]overlay=x=<final_canvas_x>:y=<final_canvas_y>:enable='between(t,start,end)'[text_v]
```

## 8. Sticker Export Flow

For each active sticker overlay:

1. `OverlayPipeline` adds sticker path as an input.
2. `StickerEngine.build_filter()` calculates target width from canvas width and sticker scale ratio.
3. FFmpeg scales with `eval=frame`, rotates, applies alpha/motion, and overlays onto current video label.

Current sticker filter shape:

```text
[sticker_input]
  scale=w='<canvas_width * scale_ratio * motion_expr>':h='-1':eval=frame,
  rotate=<degrees>*PI/180:ow=rotw(iw):oh=roth(ih):c=none,
  <alpha filter>
[sticker_src]
[current_video][sticker_src]overlay=x=<final_canvas_x>:y=<final_canvas_y>:enable='between(...)'[sticker_v]
```

## 9. MotionEngine Responsibilities

`core/overlays/motion_engine.py` owns FFmpeg expressions and preview helpers.

### Position expressions

`position_expr(x, y, motion, start, end)` returns:

- `x` expression;
- `y` expression;
- enable expression.

Base formula:

```text
x = W*x_ratio - w/2
y = H*y_ratio - h/2
enable = between(t,start,end)
```

Motion variants currently affect position for slide/bounce/drift/elastic.

### Alpha filters

`alpha_filter(motion, start, end)` currently emits:

- Fade/Fade In: `format=rgba,fade=t=in:st=start:d=0.35:alpha=1`
- Fade Out: `format=rgba,fade=t=out:st=end-0.35:d=0.35:alpha=1`
- Other: `format=rgba`

Known risk: FFmpeg `fade=alpha=1` must preserve original PNG alpha correctly. Verify with transparent stickers.

### Region scale expressions

`region_scale_expr(base_width, motion, start)` currently emits dynamic width expressions for:

- Pop/Zoom: 0.85 -> 1.12 -> 1.0 over ~0.35s.
- Bounce/Scale: 0.85 -> 1.08 -> 1.0 over ~0.55s.

The filter uses `eval=frame`; without this, scale animation would evaluate only once.

### Preview helpers

`preview_alpha()` and `preview_scale()` mirror the export concepts for canvas preview. Any future motion changes must update both preview and FFmpeg paths.

## 10. Preview Overlay Flow

`PreviewCanvas` draws on a clean source thumbnail frame, then draws safe areas and overlays. It should not reuse the composited preview as a new source.

Current preview expectations:

- text uses the same typography engine when possible;
- sticker scale is based on displayed final-canvas rect width;
- overlay positions map through normalized ratios;
- overlay visibility follows timeline playhead active ranges;
- safe-area clamping and snapping operate in normalized final-canvas space.

## 11. Mini Timeline Integration

`MiniTimeline` is overlay-only. It does not edit source video/audio/scene segments.

It controls:

- overlay start time;
- overlay end time;
- selection;
- visibility;
- playhead time.

Timeline changes call back into `MainWindow`, update `OverlayBase` timing, and trigger preview refresh.

## 12. Known Animation Bugs / Risks

These items are documented for future development and validation:

1. **Sticker Fade In can disappear.**
   - Likely caused by alpha filter interaction with existing PNG alpha or timebase.
   - Verify that `final_alpha = original_alpha * motion_alpha` behavior is preserved.

2. **Text Fade may not visually animate.**
   - Confirm the text PNG looped input uses a compatible timebase and fade `st` aligns with output timeline.

3. **Pop/Scale may not be visible enough.**
   - Expressions exist, but real FFmpeg output should be checked.
   - Requested target: Pop 0.8/0.85 -> 1.2/1.12 -> 1.0, short social overshoot.

4. **Text Scale uses width expression with `h=-1`.**
   - This should scale a PNG region, but output needs verification for text assets with alpha.

5. **Missing requested motions.**
   - Float, Shake, Pulse, Slide Left/Right, Rotate Float, speed/strength sliders are not fully implemented.

## 13. Future Motion Engine Direction

If implementing the requested full motion system, prefer a shared model like:

```python
@dataclass
class OverlayAnimation:
    preset: MotionPreset
    fade_in: bool
    fade_out: bool
    scale_mode: str
    translate_mode: str
    rotation_mode: str
    easing: str
    duration: float
    speed: float
    strength: float
```

Then produce both:

- FFmpeg expressions for export;
- Python/Qt numeric functions for preview.

Do not bake motion into PNG assets frame-by-frame unless implementing a minimal-region animated asset strategy with clear disk/RAM limits.

## 14. Animation Change Checklist

When changing motion:

- update `MotionPreset` and GUI dropdowns consistently;
- update `MotionEngine.position_expr()` for translation;
- update `MotionEngine.region_scale_expr()` for scale;
- update `MotionEngine.alpha_filter()` for opacity;
- update `preview_alpha()` and `preview_scale()`;
- add generated filter tests for text and sticker;
- test transparent PNG stickers;
- ensure `eval=frame` remains on dynamic scale filters;
- ensure overlay input is immutable and transformed once per frame;
- avoid full-frame RGBA overlay generation.

## 2026-05-09 Motion Engine Patch

The overlay animation engine now has a shared `OverlayAnimation`/`MotionEngine` path for FFmpeg export and live preview helpers.

Implemented/updated behavior:

- Fade In and Fade Out are applied as alpha fades on RGBA overlay assets after asset creation.
- Pop uses a visible social-style overshoot scale: approximately `0.80 -> 1.20 -> 1.00` over 0.30s.
- Bounce uses a softer `0.85 -> 1.08 -> 1.00` scale curve.
- Scale, Scale Up, Scale Down, Pulse, Float, Shake, Slide Left/Right/Up/Down, and Rotate Float are represented in `MotionPreset`.
- Dynamic scale filters use `eval=frame`.
- Preview alpha, scale, offset, and sticker rotate-float delta are calculated through `MotionEngine` to keep preview/export behavior aligned.

Important implementation rule:

- Do not bake animation into generated PNGs. Text/sticker assets remain immutable minimal regions; FFmpeg and preview transforms animate those regions over time.

## 2026-05-12 Realtime Motion Preview Update

Motion logic now lives in `core/motion_engine.py` and is split into explicit shared components:

- `MotionSpec`: resolved preset, timing, speed, strength, and default motion durations.
- `MotionEvaluator`: numeric easing/opacity/scale/offset/rotation evaluation.
- `PreviewTransformEvaluator`: evaluates realtime preview transform values for the current playhead timestamp.
- `FFmpegExpressionBuilder`: builds matching FFmpeg expressions for final export.

Preview and export now share the same motion source of truth. The preview canvas evaluates opacity, scale, x/y offset, and rotate-float on every paint using the current playhead timestamp, while FFmpeg receives equivalent dynamic expressions. The overlay region-only architecture remains unchanged: text and sticker assets stay as minimal RGBA regions and are never expanded into full-frame overlay sequences.

Text supports realtime preview for Fade In, Fade Out, Pop, Bounce, Pulse, Scale, Scale Up, and Scale Down. Stickers support the same transform classes plus Rotate Float. Motion speed and strength controls are now part of overlay state and affect both preview and output.

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

