---
name: record-interface-demo
description: Produce or revise a captioned e-footprint interface feature video from an agreed outline using the local Playwright recorder. Use for video authoring, not LinkedIn post drafting or publication.
---

# Record an interface demo

Start from the author's story and approved action-and-caption outline. If no outline exists, ask for the rough flow and clarify it with the author before recording. Preserve the intended example and claims. Read the interface design hub and the relevant E2E page objects or UI code only far enough to operate the current feature accurately.

Use the interface repository's `communications/video/` as the home for recording code: shared behavior in `recorder.py`, one script per video, and generated media under gitignored `output/`. Reuse the canonical model or exported example where possible, and follow the requested worktree. The local video README has run commands; Clémence's September 2026 demo kit in the workspace is a style and implementation reference when available.

Record the local development server with Playwright. Prepare imports and starting state off-camera, then show meaningful interactions at human pace with a visible cursor. Use current E2E page objects for stable selectors and HTMX waits. Keep on-screen captions brief, one idea each; they should explain the point of an action rather than narrate obvious clicks. Open with the feature and what it enables, orient the viewer through transitions, and close with the benefit. Use no narration unless requested.

Render an MP4, inspect the full video and sampled frames, and adjust script or captions until the UI, timing, tooltips, and claims are readable. Verify numerical comparisons against the example model. Leave source and final media ready for author review. Publication is a separate task.
