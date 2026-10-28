"""Iteration 4: background pipeline runs (POST /api/pipeline/runs + resumable events), critic fix fields, label, voice/test."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
sys.path.insert(0, "/app/backend")

OUTPUTS = {
    "Orchestrator": {"productName": "Ledgerly", "audience": "Small business owners", "tone": "calm", "keyMessage": "Books that balance themselves", "sceneCount": 4},
    "Planner": {"scenes": [
        {"template": "TextReveal", "purpose": "Hook", "durationSec": 2.5},
        {"template": "DeviceMockup", "purpose": "Show dashboard", "durationSec": 3},
        {"template": "Flowchart", "purpose": "How", "durationSec": 3},
        {"template": "CallToAction", "purpose": "CTA", "durationSec": 2.5}]},
    "Copywriter": {"title": "Ledgerly", "scenes": [
        {"headline": "Books that balance", "subline": "Calm finances", "detail": "LEDGERLY", "steps": [], "voiceover": ""},
        {"headline": "Everything at a glance", "subline": "", "detail": "name.app/dashboard", "steps": [], "voiceover": ""},
        {"headline": "Import to insight", "subline": "", "detail": "", "steps": ["Import", "Match", "Report"], "voiceover": ""},
        {"headline": "Start free", "subline": "", "detail": "Try Ledgerly", "steps": [], "voiceover": ""}]},
    "Designer": {"primaryColor": "#7CFFCB", "accentColor": "#55D6FF", "background": "#0B1016", "font": "Outfit"},
    "Director": {"pacing": "brisk", "scenes": [
        {"transition": "fade", "motion": "rise", "durationSec": 2.5},
        {"transition": "slide", "motion": "pop", "durationSec": 3},
        {"transition": "zoom", "motion": "drift", "durationSec": 3},
        {"transition": "wipe", "motion": "pop", "durationSec": 2.5}]},
}


def read_run(run_id, max_total=420):
    """Reconnect with after=N like the frontend until complete/error."""
    events, reconnects, t0 = [], 0, time.time()
    while time.time() - t0 < max_total:
        with requests.get(f"{BASE_URL}/api/pipeline/runs/{run_id}/events", params={"after": len(events)}, stream=True, timeout=90) as r:
            assert r.status_code == 200
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        if events and events[-1]["type"] in ("complete", "error"):
            return events, reconnects, time.time() - t0
        reconnects += 1
    raise AssertionError(f"run did not finish in {max_total}s ({len(events)} events)")


# Runs API contract
def test_unknown_run_404():
    r = requests.get(f"{BASE_URL}/api/pipeline/runs/does-not-exist/events", timeout=10)
    assert r.status_code == 404


def test_runs_invalid_continue_422():
    bad = json.loads(json.dumps(OUTPUTS))
    bad["Planner"]["scenes"][0]["template"] = "Bogus"
    r = requests.post(f"{BASE_URL}/api/pipeline/runs", json={"prompt": "Launch film", "from_agent": "Director", "outputs": bad}, timeout=20)
    assert r.status_code == 422
    assert "errors" in r.json()["detail"]


def test_runs_unknown_agent_400():
    r = requests.post(f"{BASE_URL}/api/pipeline/runs", json={"prompt": "Launch film", "from_agent": "Nobody", "outputs": OUTPUTS}, timeout=20)
    assert r.status_code == 400


# Critic fix field restriction (pure unit)
def test_apply_fixes_template_restriction():
    from agents.pipeline import apply_fixes, assemble
    project = assemble(json.loads(json.dumps(OUTPUTS)), "16:9")
    critic = {"fixes": [
        {"sceneIndex": 0, "field": "button", "value": "Nope"},
        {"sceneIndex": 1, "field": "eyebrow", "value": "NOPE"},
        {"sceneIndex": 2, "field": "eyebrow", "value": "HOW IT WORKS"},
        {"sceneIndex": 3, "field": "button", "value": "Start now"},
        {"sceneIndex": 1, "field": "headline", "value": "All in one view"}]}
    p = apply_fixes(project, critic)
    assert "button" not in p["scenes"][0]["props"]
    assert "eyebrow" not in p["scenes"][1]["props"]
    assert p["scenes"][2]["props"]["eyebrow"] == "HOW IT WORKS"
    assert p["scenes"][3]["props"]["button"] == "Start now"
    assert p["scenes"][1]["props"]["headline"] == "All in one view"
    assert p["scenes"][1]["props"]["label"] == "ledgerly.app/overview"


# Voice test per-request temp file
def test_voice_test_wav_concurrent():
    def call(i):
        return requests.post(f"{BASE_URL}/api/voice/test", json={"text": f"Sample number {i}"}, timeout=90)
    with ThreadPoolExecutor(2) as ex:
        results = list(ex.map(call, range(2)))
    for r in results:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("audio/wav")
        assert r.content[:4] == b"RIFF" and len(r.content) > 2000


# LLM: continue from Director via background run (Critic only)
@pytest.mark.llm
def test_runs_continue_from_director():
    r = requests.post(f"{BASE_URL}/api/pipeline/runs", json={"prompt": "A launch film for Ledgerly, calm bookkeeping for small businesses", "from_agent": "Director", "outputs": OUTPUTS}, timeout=20)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    events, reconnects, took = read_run(run_id)
    print(f"continue run: {len(events)} events, {reconnects} reconnects, {took:.1f}s")
    assert events[-1]["type"] == "complete", events[-1]
    project, outputs = events[-1]["project"], events[-1]["outputs"]
    assert "contrast" in outputs["Critic"]
    for s in project["scenes"]:
        if s["template"] != "CallToAction":
            assert "button" not in s["props"], s
        if s["template"] not in ("TextReveal", "Flowchart"):
            assert "eyebrow" not in s["props"], s
    mock = [s for s in project["scenes"] if s["template"] == "DeviceMockup"][0]
    assert mock["props"]["label"] == "ledgerly.app/overview"
    # replay from offset returns the tail only
    with requests.get(f"{BASE_URL}/api/pipeline/runs/{run_id}/events", params={"after": len(events) - 1}, stream=True, timeout=30) as rr:
        tail = [json.loads(l[6:]) for l in rr.iter_lines(decode_unicode=True) if l and l.startswith("data: ")]
    assert len(tail) == 1 and tail[0]["type"] == "complete"
