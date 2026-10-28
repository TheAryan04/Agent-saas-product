import asyncio
import json
import os
import shutil
import signal
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import voice_setup

RENDER_DIR = Path(os.environ["RENDER_DIR"])
RENDERER_SCRIPT = Path(os.environ["RENDERER_SCRIPT"])
FPS = 30

render_lock = asyncio.Lock()


def capabilities() -> Dict[str, Any]:
    voice = voice_setup.status()
    return {
        "remotion": bool(shutil.which("node")) and RENDERER_SCRIPT.exists(),
        "piper": voice["piper"],
        "whisper": voice["whisper"],
        "piper_fix": "open Voice setup to install Piper and a voice",
        "whisper_fix": "open Voice setup to install whisper.cpp and a caption model",
    }


async def make_voiceover(project: Dict[str, Any], public: Path) -> None:
    for i, scene in enumerate(project["scenes"]):
        line = scene["props"].get("voiceover") or scene["props"].get("headline", "")
        if not line:
            continue
        out = public / f"vo_{i}.wav"
        seconds = await asyncio.to_thread(voice_setup.synthesize, line, out)
        scene["props"]["audio"] = out.name
        scene["durationSec"] = max(float(scene["durationSec"]), round(seconds + 0.5, 1))


async def make_captions(project: Dict[str, Any], public: Path) -> List[Dict[str, Any]]:
    captions, offset = [], 0.0
    for scene in project["scenes"]:
        audio = scene["props"].get("audio")
        if audio:
            segs = await asyncio.to_thread(voice_setup.transcribe, public / audio)
            words = (scene["props"].get("voiceover") or scene["props"].get("headline", "")).split()
            counts = [max(1, len(s["text"].split())) for s in segs]
            cursor = 0
            for i, seg in enumerate(segs):
                take = len(words) - cursor if i == len(segs) - 1 else round(counts[i] / sum(counts) * len(words))
                text = " ".join(words[cursor:cursor + take]) or seg["text"]
                cursor += take
                captions.append({"start": round(offset + seg["start"], 2), "end": round(offset + seg["end"], 2), "text": text})
        offset += float(scene["durationSec"])
    return captions


class RenderJobs:
    def __init__(self, db):
        self.col = db.render_jobs
        self.procs: Dict[str, Any] = {}
        self.cancelled: set = set()
        self.tasks: set = set()

    async def reconcile(self):
        await self.col.update_many({"status": {"$in": ["queued", "running"]}}, {"$set": {"status": "error", "stage": "Render failed", "error": "Interrupted by a server restart"}})

    async def cancel(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = await self.get(job_id)
        if not job or job["status"] not in ("queued", "running"):
            return job
        self.cancelled.add(job_id)
        proc = self.procs.get(job_id)
        if proc and proc.returncode is None:
            os.killpg(proc.pid, signal.SIGKILL)
        await self._set(job_id, status="cancelled", stage="Render cancelled")
        return await self.get(job_id)

    def _check(self, job_id: str):
        if job_id in self.cancelled:
            raise asyncio.CancelledError()

    async def create(self, project: Dict[str, Any], voiceover: bool, captions: bool) -> Dict[str, Any]:
        job = {"id": str(uuid.uuid4()), "status": "queued", "stage": "Waiting for the renderer", "progress": 0.0,
               "voiceover": voiceover, "captions": captions, "error": None, "download_url": None,
               "created_at": datetime.now(timezone.utc).isoformat()}
        await self.col.insert_one(dict(job))
        task = asyncio.create_task(self._run(job["id"], project, voiceover, captions))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return job

    async def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"id": job_id}, {"_id": 0})

    async def _set(self, job_id: str, **fields):
        await self.col.update_one({"id": job_id}, {"$set": fields})

    async def _run(self, job_id: str, project: Dict[str, Any], voiceover: bool, captions: bool):
        async with render_lock:
            job_dir = RENDER_DIR / job_id
            public = job_dir / "public"
            public.mkdir(parents=True, exist_ok=True)
            try:
                self._check(job_id)
                if voiceover:
                    await self._set(job_id, status="running", stage="Synthesizing voiceover with Piper")
                    await make_voiceover(project, public)
                if voiceover and captions:
                    await self._set(job_id, status="running", stage="Transcribing captions with whisper.cpp")
                    project["captions"] = await make_captions(project, public)
                self._check(job_id)
                props = job_dir / "props.json"
                props.write_text(json.dumps({"project": project}))
                out = job_dir / "film.mp4"
                await self._set(job_id, status="running", stage="Bundling composition")
                await self._remotion(job_id, props, out, public)
                await self._set(job_id, status="done", stage="MP4 ready", progress=1.0, download_url=f"/api/render/{job_id}/download")
            except (asyncio.CancelledError, Exception) as exc:
                if job_id in self.cancelled:
                    await self._set(job_id, status="cancelled", stage="Render cancelled", progress=0.0)
                    shutil.rmtree(job_dir, ignore_errors=True)
                else:
                    await self._set(job_id, status="error", stage="Render failed", error=str(exc)[-600:])
            finally:
                self.procs.pop(job_id, None)
                self.cancelled.discard(job_id)

    async def _remotion(self, job_id: str, props: Path, out: Path, public: Path):
        proc = await asyncio.create_subprocess_exec("node", str(RENDERER_SCRIPT), str(props), str(out), str(public),
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=os.environ.copy(), start_new_session=True)
        self.procs[job_id] = proc
        tail = []
        async for raw in proc.stdout:
            line = raw.decode().strip()
            tail = (tail + [line])[-15:]
            if job_id in self.cancelled:
                continue
            if line.startswith("PROGRESS "):
                await self._set(job_id, progress=round(float(line.split()[1]), 3), stage="Rendering frames")
            elif line.startswith("STAGE "):
                await self._set(job_id, stage=line[6:])
        if await proc.wait() != 0 or not out.exists():
            raise RuntimeError("Remotion render failed: " + " | ".join(tail))
