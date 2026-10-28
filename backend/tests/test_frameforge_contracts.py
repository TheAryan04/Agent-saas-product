import json
import os
import time

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

PROJECT = {
    "title": "TEST render",
    "aspectRatio": "16:9",
    "brand": {"name": "Test", "primaryColor": "#7CFFCB", "font": "Outfit"},
    "scenes": [
        {"template": "TextReveal", "durationSec": 2, "props": {"headline": "Hello"}},
        {"template": "CallToAction", "durationSec": 2, "props": {"headline": "Go", "button": "Start"}},
    ],
}

OUTPUTS = {
    "Orchestrator": {"productName": "Orbit", "audience": "Product teams", "tone": "calm", "keyMessage": "Ship better together", "sceneCount": 3},
    "Planner": {"scenes": [
        {"template": "TextReveal", "purpose": "Hook", "durationSec": 2.5},
        {"template": "Flowchart", "purpose": "How", "durationSec": 3},
        {"template": "CallToAction", "purpose": "CTA", "durationSec": 2.5}]},
    "Copywriter": {"title": "Orbit", "scenes": [
        {"headline": "Ship better", "subline": "Calm home", "detail": "", "steps": [], "voiceover": "Ship better."},
        {"headline": "Idea to impact", "subline": "", "detail": "", "steps": ["Plan", "Build", "Launch"], "voiceover": "Plan build launch."},
        {"headline": "Start now", "subline": "", "detail": "", "steps": [], "voiceover": "Start now."}]},
    "Designer": {"primaryColor": "#7CFFCB", "accentColor": "#55D6FF", "background": "#0B1016", "font": "Outfit"},
    "Director": {"pacing": "brisk", "scenes": [
        {"transition": "fade", "motion": "rise", "durationSec": 2.5},
        {"transition": "slide", "motion": "pop", "durationSec": 3},
        {"transition": "zoom", "motion": "drift", "durationSec": 2.5}]},
}


def events_of(resp):
    return [json.loads(l[6:]) for l in resp.iter_lines(decode_unicode=True) if l and l.startswith("data: ")]


# Health
def test_ollama_health():
    d = requests.get(f"{BASE_URL}/api/health/ollama", timeout=10).json()
    assert d["running"] is True and d["model_pulled"] is True


def test_projects_contract():
    projects = requests.get(f"{BASE_URL}/api/projects", timeout=10).json()
    assert projects and "_id" not in json.dumps(projects)


# Render capabilities + voiceover guard
def test_capabilities():
    d = requests.get(f"{BASE_URL}/api/render/capabilities", timeout=10).json()
    assert d["remotion"] is True and d["piper"] is False and d["whisper"] is False


def test_render_voiceover_rejected():
    r = requests.post(f"{BASE_URL}/api/render", json={"project": PROJECT, "voiceover": True}, timeout=10)
    assert r.status_code == 400


# Pipeline continue validation
def test_continue_invalid_422():
    bad = dict(OUTPUTS, Planner={"scenes": []})
    r = requests.post(f"{BASE_URL}/api/pipeline/continue", json={"prompt": "Launch film", "from_agent": "Director", "outputs": bad}, timeout=20)
    assert r.status_code == 422
    assert r.json()["detail"]["errors"]


# Render cancel then full render
def test_render_cancel_then_complete():
    job = requests.post(f"{BASE_URL}/api/render", json={"project": PROJECT, "voiceover": False, "captions": False}, timeout=15).json()
    assert job["id"] and job["status"] == "queued"
    time.sleep(4)
    st = requests.get(f"{BASE_URL}/api/render/{job['id']}", timeout=10).json()
    assert st["status"] in ("queued", "running")
    c = requests.post(f"{BASE_URL}/api/render/{job['id']}/cancel", timeout=10).json()
    assert c["status"] == "cancelled"
    time.sleep(4)
    assert requests.get(f"{BASE_URL}/api/render/{job['id']}", timeout=10).json()["status"] == "cancelled"

    job2 = requests.post(f"{BASE_URL}/api/render", json={"project": PROJECT}, timeout=15).json()
    deadline, progresses = time.time() + 240, []
    while time.time() < deadline:
        st = requests.get(f"{BASE_URL}/api/render/{job2['id']}", timeout=10).json()
        progresses.append(st["progress"])
        if st["status"] in ("done", "error", "cancelled"):
            break
        time.sleep(4)
    assert st["status"] == "done", st
    dl = requests.get(f"{BASE_URL}/api/render/{job2['id']}/download", timeout=60)
    assert dl.status_code == 200 and dl.headers["content-type"].startswith("video/mp4") and len(dl.content) > 10000


# Pipeline continue from Director -> Critic -> complete (slow, ~60-90s)
def test_continue_from_director_runs_critic():
    with requests.post(f"{BASE_URL}/api/pipeline/continue", json={"prompt": "Launch film for Orbit", "from_agent": "Director", "outputs": OUTPUTS}, stream=True, timeout=300) as r:
        assert r.status_code == 200
        evs = events_of(r)
    agent_evs = [e for e in evs if e.get("type") == "agent"]
    assert any(e["name"] == "Critic" and e["status"] == "running" for e in agent_evs)
    assert any(e["name"] == "Critic" and e["status"] == "done" for e in agent_evs), [e for e in evs if e.get("type") != "token"][-3:]
    assert not any(e.get("name") in ("Planner", "Copywriter") for e in agent_evs)
    assert evs[-1]["type"] == "complete", evs[-1]
    assert len(evs[-1]["project"]["scenes"]) == 3
