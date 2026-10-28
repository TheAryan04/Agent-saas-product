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

## Prioritized backlog

### P0

- Connect the Ollama response to per-agent schemas and actual retry-on-validation-failure behavior.
- Implement real Remotion composition and local FFmpeg MP4 rendering with progress and download URL.

### P1

- Persist per-agent model/toggle settings and agent context with each run.
- Add reorder drag/drop and one-agent continuation from edited output.
- Add real render job status and cancellation.

### P2

- Optional Piper voiceover and whisper.cpp captions behind off-by-default flags.
- Add project search, version history, and richer template prop editors.

## Next tasks

1. Add shared Python schemas and six small agent modules.
2. Connect streaming Ollama structured output to the existing SSE route.
3. Add a local Remotion render worker and MP4 file response.