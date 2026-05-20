# AI_AGENT_RULES.md — Rules for Future AI Coding Agents

_Last updated: 2026-05-09_

Read this file before modifying code. It captures project-specific guardrails that future AI agents must follow.

## 1. Do Not Rebuild the App

The current project already contains a GUI scaffold, pipeline manager, render graph, batch renderer, overlay engines, and documentation. Future work should modify existing modules rather than replacing the architecture.

Do not:

- Delete and recreate the project.
- Split into multiple separate apps.
- Replace PySide6 with another GUI toolkit.
- Replace FFmpeg with MoviePy/OpenCV for final rendering.

## 2. Preserve Single Final Encode

All render stages before final output must be metadata/filtergraph/asset preparation stages.

Do not create intermediate MP4/H264/H265 files between stages.

Allowed temporary files:

- Minimal text PNG regions.
- Sticker/image inputs selected by user.
- Final `.rendering.mp4` before verification/rename.
- Developer-mode debug text files only when enabled.

## 3. Keep Audio Optional

Never assume a source video has audio.

When changing renderer command generation:

- Probe audio stream existence explicitly.
- Do not add audio input when no audio exists.
- Do not map audio when no audio exists.
- Do not add `-c:a` when no audio is mapped.
- Do not create fake silent tracks unless the user explicitly requests that feature later.

## 4. Do Not Shuffle Audio

Scene shuffle is video-only.

Correct model:

1. Extract original audio if present.
2. Shuffle visual segments only.
3. Compose image/fade/overlays visually.
4. Reattach original audio if present.

## 5. Respect Final-Canvas Overlay Space

Text/sticker overlays are final-canvas overlays.

Do not:

- Attach overlays to source video pixels.
- Apply overlays before image compositor/viewport shift.
- Store overlay positions as preview pixels.
- Store overlay positions as absolute output pixels.

Use normalized ratios and shared transform helpers.

## 6. Keep Minimal Overlay Assets

Text should be rendered as minimal Qt/QPainter RGBA regions.

Do not:

- Render full-frame 1080x1920 RGBA overlays per frame.
- Generate full-frame PNG sequences for normal text/sticker animation.
- Bake motion into regenerated PNG files frame-by-frame.

Motion should be applied in FFmpeg to the immutable overlay region.

## 7. Preserve Preview/Export Parity

When changing overlay motion, typography, coordinates, or safe area:

- Update preview and export logic together.
- Keep formulas/easing consistent.
- Add tests or at least command-string assertions for FFmpeg expressions.

## 8. Keep GUI Compact

Do not add large panels that push render controls out of view.

Current GUI rules:

- Left column: queue and logs.
- Center: preview and mini timeline.
- Right: workflow controls in scroll area plus fixed render/stop/open buttons.
- Safe area/snap settings remain internal; do not re-add a large Safe Area/Snap panel unless explicitly requested.

## 9. Use Existing Docs

Before implementing a major fix, read:

- `CURRENT_TASK.md`
- `KNOWN_ISSUES.md`
- `ARCHITECTURE.md`
- `RENDER_PIPELINE.md`
- `ANIMATION_SYSTEM.md`
- `FFmpeg_PIPELINE.md`
- `NEXT_SESSION_HANDOFF.md`

## 10. Keep Output Routing

Output must go to an `output/` folder beside the first queued input video.

Do not revert output to the project root unless the user explicitly changes the requirement.

## 11. Logging Rules

Normal user logs should be useful but not spammy.

Allowed normal logs:

- workflow start;
- output path;
- scene detection stage;
- image composite stage;
- overlay stage;
- final export;
- warnings/errors;
- success/failure.

Avoid normal UI spam:

- full frame-by-frame FFmpeg progress;
- giant debug graph dumps;
- painter/internal preview updates.

Developer-mode logs/files are allowed behind `ExportSettings.developer_mode`.

## 12. Testing Expectations

At minimum after code changes, run:

```bash
python -m compileall core gui models utils main.py
```

For renderer changes, also add or run focused tests/assertions for:

- FFmpeg command maps;
- audio/no-audio behavior;
- filtergraph labels;
- fade crop math;
- overlay motion expressions;
- output path selection.

## 13. Commit and PR Discipline

For this environment:

- Commit changes on the current branch.
- Create a PR record after committing.
- Do not create a PR if no code/docs changed.

## 14. Overlay Motion Patch Rules

After the 2026-05-09 motion patch, text and sticker motion must continue to use the shared `MotionEngine`.

Rules:

- Add new motion presets to `models.overlay.MotionPreset` first.
- Add matching FFmpeg and preview behavior in `core/overlays/motion_engine.py`.
- Apply motion after immutable RGBA overlay asset creation.
- Keep scale animation in FFmpeg `scale=...:eval=frame`.
- Keep fade as alpha animation on RGBA overlay streams.
- Keep preview transforms routed through the same motion helper formulas.

## 15. Realtime Motion Preview Rule

After the 2026-05-12 realtime motion update, preview and export motion must both route through `core/motion_engine.py`.

Rules:

- Use `MotionSpec` for timing, speed, strength, and selected preset.
- Use `PreviewTransformEvaluator` for live preview transforms.
- Use `FFmpegExpressionBuilder` for export filter expressions.
- Do not reintroduce separate preview-only formulas in `gui/preview_canvas.py`.
- Do not replace region-only overlay animation with full-frame RGBA canvases.

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

