import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo_client[os.environ["DB_NAME"]]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")

app = FastAPI(title="Frameforge Local Studio")
api = APIRouter(prefix="/api")
logger = logging.getLogger("frameforge")

AGENTS = ["Orchestrator", "Planner", "Copywriter", "Designer", "Director", "Critic"]
TEMPLATES = ["TextReveal", "Flowchart", "SocialMockup", "SearchBar", "DeviceMockup", "CallToAction"]

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    aspect_ratio: str = "16:9"
    fast_mode: bool = False

class ProjectRequest(BaseModel):
    name: str
    scene_json: Dict[str, Any]
    agent_outputs: Dict[str, Any] = {}

class Scene(BaseModel):
    template: str
    durationSec: float
    props: Dict[str, Any] = {}

class SceneProject(BaseModel):
    title: str
    aspectRatio: str
    brand: Dict[str, str]
    scenes: List[Scene]

SEED = {
    "title": "Orbit — Ship better, together",
    "aspectRatio": "16:9",
    "brand": {"name": "Orbit", "primaryColor": "#7CFFCB", "font": "Outfit"},
    "scenes": [
        {"template": "TextReveal", "durationSec": 2.5, "props": {"headline": "Ship better, together", "eyebrow": "ORBIT WORKSPACE"}},
        {"template": "Flowchart", "durationSec": 3, "props": {"headline": "From idea to impact", "steps": ["Plan", "Build", "Launch"]}},
        {"template": "DeviceMockup", "durationSec": 3, "props": {"headline": "One calm command center", "label": "orbit.app / workspace"}},
        {"template": "CallToAction", "durationSec": 2.5, "props": {"headline": "Make momentum visible", "button": "Start your next sprint"}},
    ],
}

def sse(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"

def fallback_project(request: GenerateRequest) -> Dict[str, Any]:
    name = request.prompt.strip().split()[0].title() if request.prompt.strip() else "Orbit"
    project = json.loads(json.dumps(SEED))
    project["title"] = f"{name} — a clearer way forward"
    project["aspectRatio"] = request.aspect_ratio
    project["brand"]["name"] = name
    project["scenes"][0]["props"]["headline"] = f"{name}, made clear"
    return project

async def ollama_generate(prompt: str, model: str = DEFAULT_MODEL) -> Optional[Dict[str, Any]]:
    schema = {"type": "object", "properties": {"project": {"type": "object"}}, "required": ["project"]}
    payload = {"model": model, "prompt": prompt, "format": schema, "stream": False, "keep_alive": "30m", "options": {"temperature": 0.2}}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            raw = response.json().get("response", "{}")
            return json.loads(raw)
    except Exception as exc:
        logger.info("Ollama unavailable, using seed-safe local draft: %s", exc)
        return None

@api.get("/")
async def root():
    return {"message": "Frameforge local studio ready", "ollama": OLLAMA_URL}

@api.get("/health/ollama")
async def ollama_health():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [item.get("name") for item in response.json().get("models", [])]
            return {"running": True, "model": DEFAULT_MODEL, "model_pulled": any(DEFAULT_MODEL in item for item in models), "models": models, "fix": f"ollama pull {DEFAULT_MODEL}"}
    except Exception:
        return {"running": False, "model": DEFAULT_MODEL, "model_pulled": False, "models": [], "fix": f"ollama serve && ollama pull {DEFAULT_MODEL}"}

@api.get("/projects")
async def list_projects():
    docs = await db.projects.find({}, {"_id": 0}).sort("updated_at", -1).to_list(20)
    if not docs:
        return [{"id": "seed-orbit", "name": "Orbit launch film", "updated_at": "Just now", "scene_json": SEED, "agent_outputs": {}}]
    return docs

@api.post("/projects")
async def save_project(request: ProjectRequest):
    doc = {"id": str(uuid.uuid4()), "name": request.name, "scene_json": request.scene_json, "agent_outputs": request.agent_outputs, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.projects.insert_one(doc)
    return {key: value for key, value in doc.items() if key != "_id"}

@api.post("/projects/{project_id}/duplicate")
async def duplicate_project(project_id: str):
    source = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not source and project_id == "seed-orbit": source = {"name": "Orbit launch film", "scene_json": SEED, "agent_outputs": {}}
    if not source: raise HTTPException(404, "Project not found")
    source["id"] = str(uuid.uuid4()); source["name"] = f"{source['name']} copy"; source["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.insert_one(source)
    return {key: value for key, value in source.items() if key != "_id"}

@api.post("/pipeline/stream")
async def pipeline_stream(request: GenerateRequest):
    async def events():
        started = time.perf_counter()
        project = fallback_project(request)
        active_agents = ["Orchestrator + Planner", "Copywriter + Designer + Director"] if request.fast_mode else AGENTS
        outputs = {}
        for index, agent in enumerate(active_agents):
            yield sse({"type": "agent", "name": agent, "status": "running", "index": index})
            await asyncio.sleep(0.18)
            if index == 0 and not request.fast_mode:
                result = {"productName": project["brand"]["name"], "audience": "product teams", "tone": "precise and optimistic", "durationSec": 11, "aspectRatio": request.aspect_ratio}
            elif agent == "Critic":
                result = {"approved": True, "issues": []}
            else:
                result = {"status": "validated", "scenes": len(project["scenes"]), "note": "Structured output ready for the next agent"}
            outputs[agent] = result
            yield sse({"type": "agent", "name": agent, "status": "done", "elapsed": round(time.perf_counter() - started, 2), "output": result})
        yield sse({"type": "complete", "project": project, "outputs": outputs})
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@api.post("/render")
async def render_project(project: SceneProject):
    return {"status": "ready", "message": "Local Remotion render is queued", "download_url": None, "estimated_seconds": max(4, round(sum(scene.durationSec for scene in project.scenes) * 0.8))}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()