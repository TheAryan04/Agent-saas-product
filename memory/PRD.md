# Frameforge Local Motion Studio PRD

## Original problem statement

Build a free, fully local web app that turns a text prompt into an editable motion-graphics product/SaaS video through a sequential Ollama multi-agent pipeline, with preview, scene editing, export, projects, settings, and CPU-friendly defaults. Preserve the existing React/FastAPI structure rather than replacing it with Next.js.

## Architecture decisions

- React JavaScript + Tailwind-style CSS remains the frontend because the existing workspace is CRA/Craco.
- FastAPI remains the backend and exposes health, project persistence, SSE pipeline, and render contracts.
- Existing MongoDB environment variables remain the persistence source.
- Ollama is server-side only, uses structured JSON intent, and receives `keep_alive: "30m"`.
- A seed-safe fallback lets the studio open and remain editable when Ollama or FFmpeg is unavailable.

## Personas

- Solo product marketer creating a short launch film on a laptop.
- Founder shaping SaaS messaging without motion-design software.
- Technical user inspecting and tuning a local agent pipeline.

## Core requirements

- Prompt input, aspect ratio, fast mode, sequential agent timeline, scene preview, editable scene list, save/projects, settings, health check, and export action.
- Responsive dark accessible studio UI with data-test IDs on user-facing flows.
- Fictional brands and original visual language only.

## Implemented (2026-10-28)

- Frameforge studio shell with electric mint Studio Pro visual system.
- Seed Orbit project with TextReveal, Flowchart, DeviceMockup, and CallToAction preview states.
- SSE pipeline contract with sequential agent progress, fast mode, outputs, and final project.
- Scene selection, template/headline/duration editing, add/delete, scrubber, playback, save notice, and export notice.
- Projects library with reopen and duplicate controls.
- Settings page with per-agent model/toggle controls and Ollama health/fix command.
- Backend health, projects, duplicate, SSE pipeline, and render endpoints.
- README and protected environment compatibility.

## Implemented (2026-06, iteration 3)

- Real Ollama pipeline: backend/agents/ (schemas, ollama client, definitions, pipeline). Sequential agents, JSON-schema structured output, streaming tokens over SSE, 1 retry on validation failure, scene-count checks, Critic fixes applied.
- Offline handling: clear ollama_offline / model-missing errors, no fake output.
- /api/pipeline/continue: edit any agent output, rerun only later agents.
- Remotion composition shared by preview (@remotion/player) and export (frontend/src/remotion/*, frontend/renderer/render.mjs).
- Render jobs: POST /api/render -> job id, GET /api/render/{id}, /download, /capabilities (backend/render_jobs.py, Mongo render_jobs).
- Optional Piper voiceover + whisper.cpp captions behind export toggles (off by default, env PIPER_*/WHISPER_*).
- Scene drag-drop + up/down reorder; per-agent model/enable settings in localStorage.
- Frontend split into components/studio/* and hooks/usePipeline.js.

## Verification status (iteration 4)

- Full 6-agent Ollama run completed end-to-end (~4 min on pod CPU). Fixed schema-inliner bug that dropped the Copywriter `title` field.
- Copywriter now uses a compact per-scene `detail` field mapped to template props; Flowchart steps enforced via retry check.
- Brand fonts bundled locally via @fontsource (Outfit, Manrope, Sora, IBM Plex Sans, Space Mono, DM Mono) with delayRender font loading.
- Render cancel: POST /api/render/{id}/cancel kills the renderer process group; UI Cancel button. Stale jobs reconciled on startup.
- Testing agent iteration_2 (re-run): backend 7/7, frontend 100%.
- Known: fast mode merged step can take >3 min on CPU (large combined JSON). Piper/whisper paths untested (not installed).

## Verification status

- Remotion MP4 render verified directly (seed project, ~95s). Offline/model-missing errors verified.
- NOT yet verified: full real Ollama run end-to-end (Ollama kept dying in the pod; binary at /root/ollama/bin/ollama), render via API from UI, continue flow, Piper/whisper paths. Testing agent not run this iteration.
- backend/tests/test_frameforge_contracts.py render test is outdated (render now returns a job).

## Next tasks

1. Run full Ollama pipeline e2e, fix issues; run testing agent.
2. Update contract tests for new render/continue APIs.
3. Render cancellation, project update-in-place, project search/version history.
