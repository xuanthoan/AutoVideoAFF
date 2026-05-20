# DECISIONS.md — Architecture and Product Decisions

_Last updated: 2026-05-09_

This document records important decisions already made so future sessions do not reopen or accidentally reverse them.

## 1. One Unified Application

Decision: AutoVideoAFF remains one desktop app, not separate apps for shuffle, compositor, overlays, or export.

Reason:

- User workflow is mass production with minimal clicks.
- Splitting tools would force intermediate exports/imports and slow batch production.

## 2. FFmpeg Is the Final Rendering Engine

Decision: Final video compositing/export uses FFmpeg through subprocess orchestration.

Allowed Python roles:

- GUI.
- Project state.
- Render planning.
- FFmpeg command building.
- Temporary minimal overlay asset generation.
- Process management.

Not allowed:

- MoviePy final render pipeline.
- OpenCV final compositor.
- Recursive QPainter/framebuffer capture as final video output.

## 3. Single Final Encode

Decision: The renderer must keep one final encode per output video.

Allowed:

- Metadata stages.
- FilterGraph stages.
- Temporary PNG text/sticker assets.
- Temporary `.rendering.mp4` final output file before verification/rename.

Not allowed:

- Stage 1 MP4 -> Stage 2 MP4 -> Stage 3 MP4.
- H264/H265 intermediate generation.
- Re-importing intermediate videos.

## 4. Multi-Stage Logic Pipeline

Decision: The pipeline is logically staged but physically merged into one final FFmpeg command.

Logical stages:

1. Shuffle plan.
2. Layout plan.
3. Image compositor/fade plan.
4. Overlay plan.
5. Final export.

Reason:

- Easier to debug than one giant procedural filter string.
- Keeps single final encode.
- Supports modular workflow modes.

## 5. Four Workflow Modes

Decision: The app supports exactly four production workflow modes for now:

1. Shuffle + Image.
2. Shuffle + Image + Overlay.
3. Shuffle + Overlay.
4. Overlay Only.

Only one mode is active at a time.

## 6. Audio Is Optional and Must Never Be Shuffled

Decision: Scene shuffle affects only video frames.

Rules:

- Audio must never be segmented/shuffled.
- If audio exists, extract/remux original audio into final output.
- If audio does not exist, export video-only MP4.
- Do not create fake silent audio tracks.

Status:

- This is a decided architecture rule, but implementation still needs a full no-audio fix.

## 7. Overlay Coordinate System

Decision: Text and sticker overlays use normalized final-canvas center coordinates.

Rules:

- `x=0.5, y=0.5` means final canvas center.
- Coordinates are not preview widget pixels.
- Coordinates are not raw source video pixels.
- Dragging in preview must convert display pixels back into normalized ratios.

## 8. Sticker Scale System

Decision: Sticker scale is canvas-width-relative.

Example:

- `scale=0.16` means sticker target width is about `canvas_width * 0.16`.

Not allowed:

- Scaling based on preview widget pixels.
- Scaling based only on source sticker dimensions.

## 9. Text Typography Rendering

Decision: Final social typography is rendered by Qt/QPainter into minimal transparent PNG regions, then composited by FFmpeg.

Reason:

- FFmpeg `drawtext` did not match preview typography quality.
- Qt/QPainter gives better antialiasing, rounded background, multiline layout, padding, and optical alignment.

Rules:

- Do not return to raw FFmpeg `drawtext` for final typography.
- Do not render full-frame text canvases.
- Render only minimal bounding-box RGBA text regions.

## 10. Text Box Shadow

Decision: Text background boxes should be flat rounded rectangles with no outer/drop shadow.

Allowed:

- Font antialiasing.
- Text styling from templates.

Not allowed:

- Dark halo behind text box.
- Outer glow behind box.
- Drop shadow behind box.

## 11. Overlay Layer Order

Decision: Overlays are final post-composition layers.

Order:

1. base canvas
2. image layer
3. shifted/cropped main video layer
4. fade layer
5. text overlays
6. sticker overlays

Text/sticker must not be applied before viewport/image compositing.

## 12. Image/Fade Layout

Decision: Image compositor uses dynamic percentage layout, not hardcoded `65/5/35` values.

Rules:

- `image_height_percent` default 35, range 20-60.
- `overlap_percent` default 5, range `0..min(20, image_height_percent)`.
- Fade region is the shifted video region overlapping the image.
- Fade source crop uses `source_y = fade_start - offset_y`.

## 13. Safe Area and Snap

Decision: Safe area and snap are core editor behaviors enabled internally by default.

Rules:

- Do not show a separate Safe Area/Snap panel in the current compact GUI.
- Default platform preset is TikTok.
- Safe area applies to final canvas, not raw source video.

## 14. Output Folder

Decision: Output goes beside the first queued video.

Example:

```text
Input:  D:/CampaignA/video1.mp4
Output: D:/CampaignA/output/video1.mp4
```

If the queue includes videos from multiple folders, the first video determines the output root.

## 15. Debug Artifacts

Decision: `debug_filtergraph.txt` and `debug_fade_filter.txt` are developer-mode artifacts only.

Default release behavior:

- Do not write debug text files.
- Export final video only, plus temporary files that are cleaned.

## 16. Mini Timeline Scope

Decision: Mini Timeline is only for overlay timing.

Allowed:

- Overlay start/end.
- Drag/resize overlay duration.
- Playhead preview.
- Text/sticker visibility.

Not allowed:

- Full NLE timeline.
- Video track editing.
- Audio waveform editing.
- Complex keyframe editor.

## 17. Documentation Strategy

Decision: Keep internal docs in Markdown files at repo root.

Current key docs:

- `ARCHITECTURE.md`
- `RENDER_PIPELINE.md`
- `ANIMATION_SYSTEM.md`
- `FFmpeg_PIPELINE.md`
- `PROJECT_STATUS.md`
- `BUGS.md`
- `NEXT_SESSION_HANDOFF.md`
- `CURRENT_TASK.md`
- `DECISIONS.md`
- `AI_AGENT_RULES.md`
- `TESTING.md`
- `KNOWN_ISSUES.md`
- `FILE_STRUCTURE.md`

## 18. Motion Engine Source of Truth

Decision: `core/overlays/motion_engine.py` is the shared source of truth for overlay motion in both preview and export.

Rules:

- Text and sticker engines should call `MotionEngine` instead of duplicating expressions.
- Preview canvas should call `MotionEngine` helper methods instead of hardcoding separate animation math.
- Animated scale must use region transforms, not regenerated PNG assets.
- Fade must animate RGBA overlay alpha after asset creation.

## 19. Shared Realtime Motion Evaluator

Decision: realtime preview and FFmpeg export must use the shared motion evaluator in `core/motion_engine.py`.

Rules:

- `MotionSpec` is the shared data contract.
- Preview uses numeric transform evaluation.
- Export uses FFmpeg expression generation from the same timing/speed/strength model.
- Motion preview must not require full render and must not use full-frame RGBA overlay canvases.

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

