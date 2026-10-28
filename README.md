# Frameforge Local Motion Studio

Frameforge turns a short product brief into an editable motion-graphics draft. It is designed for a CPU-only machine and keeps the workflow local: React for the studio UI, FastAPI for the pipeline API, MongoDB for saved projects, and Ollama for optional structured generation.

## Prerequisites

- Node 18+ and Yarn
- Python 3.11+
- MongoDB running at the existing `MONGO_URL`
- Ollama (optional for the seed-safe demo), with local FFmpeg available for a future renderer

```bash
ollama serve
ollama pull qwen2.5-coder:3b
```

## Run

The workspace uses the existing supervisor-managed services. For a manual run:

```bash
cd frontend && yarn start
cd backend && uvicorn server:app --host 0.0.0.0 --port 8001
```

Configuration lives in the existing environment files. Add `OLLAMA_URL` and `OLLAMA_MODEL` to the backend environment when enabling local generation; per-agent overrides can be added later as `OLLAMA_MODEL_ORCHESTRATOR`, etc. Protected MongoDB and frontend URL values must remain unchanged.

## Workflow

1. Enter a brief and choose 16:9 or 9:16.
2. Generate the draft; agents advance sequentially and emit progress through SSE.
3. Select scenes, edit copy, template, and timing, then use the preview scrubber.
4. Save the project to local persistence or reopen it from Projects.
5. Export when the local Remotion/FFmpeg renderer is configured.

## Adding templates and agents

Templates are represented by the named scene types in `frontend/src/App.js` and can be added to `TEMPLATES` plus a preview branch. The backend pipeline stages live in `backend/server.py`; each stage should keep its structured output short, validate it before forwarding it, and remain awaited in order.

## Troubleshooting

- **Ollama offline:** run `ollama serve`, then `ollama pull qwen2.5-coder:3b`. The seed project remains editable without Ollama.
- **Slow generation:** use Fast mode, keep prompts concise, and keep the model at `keep_alive: "30m"`.
- **Out of memory:** use the 3B model, reduce scene count, and keep draft resolution at 1280×720.
- **Render failures:** confirm FFmpeg is installed and that only one render job is active.

The current render endpoint is **MOCKED**: it reports a local queue status but does not yet produce an MP4 download. The offline Ollama path is also **MOCKED** with a deterministic seed-safe draft. These fallbacks are intentional so the editor works before local services are installed.

Remotion has its own license terms. Review the current Remotion license before using its renderer in a commercial workflow.