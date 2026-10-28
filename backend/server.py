import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, StreamingResponse  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agents import ollama, pipeline  # noqa: E402
from agents.definitions import AGENTS  # noqa: E402
from agents.schemas import SceneProject  # noqa: E402
from render_jobs import RENDER_DIR, RenderJobs, capabilities  # noqa: E402

mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo_client[os.environ["DB_NAME"]]
jobs = RenderJobs(db)

app = FastAPI(title="Frameforge Local Studio")
api = APIRouter(prefix="/api")
logger = logging.getLogger("frameforge")

SEED = {
    "title": "Orbit — Ship better, together",
    "aspectRatio": "16:9",
    "brand": {"name": "Orbit", "primaryColor": "#7CFFCB", "accentColor": "#55D6FF", "background": "#0B1016", "font": "Outfit"},
    "scenes": [
        {"template": "TextReveal", "durationSec": 2.5, "props": {"headline": "Ship better, together", "eyebrow": "ORBIT WORKSPACE", "subline": "A calm home for product teams.", "transition": "fade", "motion": "rise"}},
        {"template": "Flowchart", "durationSec": 3, "props": {"headline": "From idea to impact", "steps": ["Plan", "Build", "Launch"], "transition": "slide", "motion": "pop"}},
        {"template": "DeviceMockup", "durationSec": 3, "props": {"headline": "One calm command center", "label": "orbit.app / workspace", "transition": "zoom", "motion": "drift"}},
        {"template": "CallToAction", "durationSec": 2.5, "props": {"headline": "Make momentum visible", "button": "Start your next sprint", "transition": "wipe", "motion": "pop"}},
    ],
}


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    aspect_ratio: str = "16:9"
    fast_mode: bool = False
    models: Dict[str, str] = {}
    enabled: Dict[str, bool] = {}


class ContinueRequest(GenerateRequest):
    from_agent: str
    outputs: Dict[str, Any]


class ProjectRequest(BaseModel):
    name: str
    scene_json: Dict[str, Any]
    agent_outputs: Dict[str, Any] = {}


class RenderRequest(BaseModel):
    project: SceneProject
    voiceover: bool = False
    captions: bool = False


def sse_response(events):
    async def body():
        async for event in events:
            yield f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
    return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api.get("/")
async def root():
    return {"message": "Frameforge local studio ready", "ollama": ollama.OLLAMA_URL}


@api.get("/health/ollama")
async def ollama_health():
    return await ollama.health()


@api.get("/projects")
async def list_projects():
    docs = await db.projects.find({}, {"_id": 0}).sort("updated_at", -1).to_list(50)
    return docs or [{"id": "seed-orbit", "name": "Orbit launch film", "updated_at": "Just now", "scene_json": SEED, "agent_outputs": {}}]


@api.post("/projects")
async def save_project(request: ProjectRequest):
    doc = {"id": str(uuid.uuid4()), "name": request.name, "scene_json": request.scene_json, "agent_outputs": request.agent_outputs, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.projects.insert_one(dict(doc))
    return doc


@api.post("/projects/{project_id}/duplicate")
async def duplicate_project(project_id: str):
    source = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not source and project_id == "seed-orbit":
        source = {"name": "Orbit launch film", "scene_json": SEED, "agent_outputs": {}}
    if not source:
        raise HTTPException(404, "Project not found")
    source.update(id=str(uuid.uuid4()), name=f"{source['name']} copy", updated_at=datetime.now(timezone.utc).isoformat())
    await db.projects.insert_one(dict(source))
    return source


@api.post("/pipeline/stream")
async def pipeline_stream(request: GenerateRequest):
    return sse_response(pipeline.run(request.prompt, request.aspect_ratio, request.fast_mode, request.models, request.enabled))


@api.post("/pipeline/continue")
async def pipeline_continue(request: ContinueRequest):
    if request.from_agent not in AGENTS:
        raise HTTPException(400, f"Unknown agent {request.from_agent}")
    outputs = dict(request.outputs)
    errors = pipeline.validate_outputs(outputs, request.from_agent)
    if errors:
        raise HTTPException(422, {"message": "Edited output does not match the agent schema", "errors": errors})
    return sse_response(pipeline.run(request.prompt, request.aspect_ratio, False, request.models, request.enabled, outputs, request.from_agent))


@api.get("/render/capabilities")
async def render_capabilities():
    return capabilities()


@api.post("/render")
async def render_project(request: RenderRequest):
    caps = capabilities()
    if not caps["remotion"]:
        raise HTTPException(503, "Remotion renderer is not available. Run `yarn install` in frontend/.")
    if request.voiceover and not caps["piper"]:
        raise HTTPException(400, caps["piper_fix"])
    if request.captions and (not request.voiceover or not caps["whisper"]):
        raise HTTPException(400, "Captions need voiceover enabled and whisper.cpp installed. " + caps["whisper_fix"])
    return await jobs.create(request.project.model_dump(exclude_none=True), request.voiceover, request.captions)


@api.get("/render/{job_id}")
async def render_status(job_id: str):
    job = await jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Render job not found")
    return job


@api.post("/render/{job_id}/cancel")
async def render_cancel(job_id: str):
    job = await jobs.cancel(job_id)
    if not job:
        raise HTTPException(404, "Render job not found")
    return job


@api.get("/render/{job_id}/download")
async def render_download(job_id: str):
    job = await jobs.get(job_id)
    path = RENDER_DIR / job_id / "film.mp4"
    if not job or job["status"] != "done" or not path.exists():
        raise HTTPException(404, "MP4 not ready")
    return FileResponse(path, media_type="video/mp4", filename="frameforge-film.mp4")


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
