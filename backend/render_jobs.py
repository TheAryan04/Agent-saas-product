import asyncio
import json
import os
import shutil
import signal
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

RENDER_DIR = Path(os.environ["RENDER_DIR"])
RENDERER_SCRIPT = Path(os.environ["RENDERER_SCRIPT"])
PIPER_BIN = os.environ.get("PIPER_BIN", "piper")
PIPER_MODEL = os.environ.get("PIPER_MODEL", "")
WHISPER_BIN = os.environ.get("WHISPER_BIN", "whisper-cli")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "")
FPS = 30

render_lock = asyncio.Lock()


def capabilities() -> Dict[str, Any]:
    piper = bool(shutil.which(PIPER_BIN)) and bool(PIPER_MODEL) and Path(PIPER_MODEL).exists()
    whisper = bool(shutil.which(WHISPER_BIN)) and bool(WHISPER_MODEL) and Path(WHISPER_MODEL).exists()
    return {
        "remotion": bool(shutil.which("node")) and RENDERER_SCRIPT.exists(),
        "piper": piper,
        "whisper": whisper,
        "piper_fix": "Install Piper and set PIPER_BIN + PIPER_MODEL (.onnx voice) in backend/.env",
        "whisper_fix": "Build whisper.cpp and set WHISPER_BIN + WHISPER_MODEL (ggml-base.en.bin) in backend/.env",
    }


async def run_cmd(*args: str, stdin: Optional[str] = None) -> str:
    proc = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate(stdin.encode() if stdin else None)
    if proc.returncode != 0:
        raise RuntimeError(f"{Path(args[0]).name} failed: {err.decode()[-400:]}")
    return out.decode()


def wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as audio:
        return audio.getnframes() / float(audio.getframerate())


async def make_voiceover(project: Dict[str, Any], public: Path) -> None:
    for i, scene in enumerate(project["scenes"]):
        line = scene["props"].get("voiceover") or scene["props"].get("headline", "")
        if not line:
            continue
        out = public / f"vo_{i}.wav"
        await run_cmd(PIPER_BIN, "--model", PIPER_MODEL, "--output_file", str(out), stdin=line)
        scene["props"]["audio"] = out.name
        scene["durationSec"] = max(float(scene["durationSec"]), round(wav_seconds(out) + 0.4, 1))


async def make_captions(project: Dict[str, Any], public: Path) -> List[Dict[str, Any]]:
    captions, offset = [], 0.0
    for scene in project["scenes"]:
        audio = scene["props"].get("audio")
        if audio:
            base = public / Path(audio).stem
            await run_cmd(WHISPER_BIN, "-m", WHISPER_MODEL, "-f", str(public / audio), "-oj", "-of", str(base))
            data = json.loads(Path(f"{base}.json").read_text())
            for seg in data.get("transcription", []):
                o = seg["offsets"]
                captions.append({"start": round(offset + o["from"] / 1000, 2), "end": round(offset + o["to"] / 1000, 2), "text": seg["text"].strip()})
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
