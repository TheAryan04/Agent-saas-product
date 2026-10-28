import asyncio
import importlib
import importlib.util
import json
import os
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List

import httpx

VOICE_DIR = Path(os.environ["VOICE_DIR"])
CONFIG = VOICE_DIR / "config.json"
HF_PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
HF_WHISPER = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

VOICES = {
    "en_US-lessac-medium": {"label": "Lessac · US English · warm, neutral", "path": "en/en_US/lessac/medium", "size_mb": 63},
    "en_US-amy-medium": {"label": "Amy · US English · bright", "path": "en/en_US/amy/medium", "size_mb": 63},
    "en_GB-alan-medium": {"label": "Alan · British English · calm", "path": "en/en_GB/alan/medium", "size_mb": 63},
}
WHISPER_MODELS = {
    "tiny.en": {"label": "tiny.en · fastest, fine for clean narration", "size_mb": 75},
    "base.en": {"label": "base.en · more accurate, ~2× slower", "size_mb": 142},
}
PACKAGES = {"piper_engine": "piper-tts==1.8.0", "whisper_engine": "pywhispercpp==1.5.1"}

tasks: Dict[str, Dict[str, Any]] = {}
_running: set = set()


def config() -> Dict[str, str]:
    saved = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    return {"voice": "en_US-lessac-medium", "whisper_model": "tiny.en", **saved}


def save_config(**values):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({**config(), **values}))


def voice_path(voice: str) -> Path:
    return VOICE_DIR / f"{voice}.onnx"


def whisper_path(model: str) -> Path:
    return VOICE_DIR / f"ggml-{model}.bin"


def has_module(name: str) -> bool:
    importlib.invalidate_caches()
    return importlib.util.find_spec(name) is not None


def status() -> Dict[str, Any]:
    cfg = config()
    piper_engine, whisper_engine = has_module("piper"), has_module("pywhispercpp")
    voice_ready = voice_path(cfg["voice"]).exists() and Path(f"{voice_path(cfg['voice'])}.json").exists()
    model_ready = whisper_path(cfg["whisper_model"]).exists()
    return {
        "config": cfg,
        "steps": {"piper_engine": piper_engine, "voice": voice_ready, "whisper_engine": whisper_engine, "whisper_model": model_ready},
        "piper": piper_engine and voice_ready,
        "whisper": whisper_engine and model_ready,
        "voices": [{"id": k, **v, "downloaded": voice_path(k).exists()} for k, v in VOICES.items()],
        "whisper_models": [{"id": k, **v, "downloaded": whisper_path(k).exists()} for k, v in WHISPER_MODELS.items()],
        "manual": {
            "piper_engine": f"{Path(sys.executable).name} -m pip install {PACKAGES['piper_engine']}",
            "voice": f"curl -L -o {voice_path(cfg['voice'])} {HF_PIPER}/{VOICES[cfg['voice']]['path']}/{cfg['voice']}.onnx  (and the matching .onnx.json)",
            "whisper_engine": f"{Path(sys.executable).name} -m pip install {PACKAGES['whisper_engine']}",
            "whisper_model": f"curl -L -o {whisper_path(cfg['whisper_model'])} {HF_WHISPER}/ggml-{cfg['whisper_model']}.bin",
        },
        "tasks": tasks,
    }


def _task(name: str, **fields):
    tasks[name] = {**tasks.get(name, {}), **fields}


async def _pip(name: str):
    proc = await asyncio.create_subprocess_exec(sys.executable, "-m", "pip", "install", "--disable-pip-version-check", PACKAGES[name],
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    async for raw in proc.stdout:
        _task(name, log=raw.decode().strip()[-160:])
    if await proc.wait() != 0:
        raise RuntimeError(f"pip install failed: {tasks[name].get('log')}")


async def _download(name: str, files: List[tuple]):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15), follow_redirects=True) as client:
        for url, target in files:
            part = target.with_suffix(target.suffix + ".part")
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total, done = int(response.headers.get("content-length", 0)), 0
                with part.open("wb") as handle:
                    async for chunk in response.aiter_bytes(1 << 16):
                        handle.write(chunk)
                        done += len(chunk)
                        if total:
                            _task(name, progress=round(done / total, 3), log=f"{target.name}: {done >> 20} / {total >> 20} MB")
            part.rename(target)


async def _run(name: str, choice: str):
    try:
        if name in PACKAGES:
            await _pip(name)
        elif name == "voice":
            base = f"{HF_PIPER}/{VOICES[choice]['path']}/{choice}"
            await _download(name, [(f"{base}.onnx.json", Path(f"{voice_path(choice)}.json")), (f"{base}.onnx", voice_path(choice))])
            save_config(voice=choice)
        elif name == "whisper_model":
            await _download(name, [(f"{HF_WHISPER}/ggml-{choice}.bin", whisper_path(choice))])
            save_config(whisper_model=choice)
        _task(name, status="done", progress=1.0, log="Ready")
    except Exception as exc:
        _task(name, status="error", log=str(exc)[-300:])
    finally:
        _running.discard(name)


def start(name: str, choice: str = "") -> Dict[str, Any]:
    if name not in ("piper_engine", "voice", "whisper_engine", "whisper_model"):
        raise ValueError("Unknown setup step")
    if name == "voice" and choice not in VOICES:
        raise ValueError("Unknown voice")
    if name == "whisper_model" and choice not in WHISPER_MODELS:
        raise ValueError("Unknown caption model")
    if name in _running:
        return tasks[name]
    if name == "voice" and voice_path(choice).exists():
        save_config(voice=choice)
        _task(name, status="done", progress=1.0, log="Already downloaded — selected")
        return tasks[name]
    if name == "whisper_model" and whisper_path(choice).exists():
        save_config(whisper_model=choice)
        _task(name, status="done", progress=1.0, log="Already downloaded — selected")
        return tasks[name]
    _running.add(name)
    _task(name, status="running", progress=0.0, log="Starting…")
    task = asyncio.create_task(_run(name, choice))
    _refs.add(task)
    task.add_done_callback(_refs.discard)
    return tasks[name]


_refs: set = set()


def synthesize(text: str, out: Path) -> float:
    from piper import PiperVoice
    voice = PiperVoice.load(str(voice_path(config()["voice"])))
    with wave.open(str(out), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    with wave.open(str(out)) as audio:
        return audio.getnframes() / float(audio.getframerate())


def transcribe(wav: Path) -> List[Dict[str, Any]]:
    import numpy as np
    from pywhispercpp.model import Model
    with wave.open(str(wav)) as audio:
        rate, frames = audio.getframerate(), audio.readframes(audio.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    resampled = np.interp(np.arange(0, len(samples), rate / 16000), np.arange(len(samples)), samples).astype(np.float32)
    model = Model(str(whisper_path(config()["whisper_model"])), n_threads=max(1, (os.cpu_count() or 2) // 2), print_progress=False, print_realtime=False)
    return [{"start": seg.t0 / 100, "end": seg.t1 / 100, "text": seg.text.strip()} for seg in model.transcribe(resampled)]
