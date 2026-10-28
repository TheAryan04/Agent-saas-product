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
    assert d["remotion"] is True and d["piper"] is True and d["whisper"] is True


def test_render_captions_without_voiceover_rejected():
    r = requests.post(f"{BASE_URL}/api/render", json={"project": PROJECT, "voiceover": False, "captions": True}, timeout=10)
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


# Voice setup API
def test_voice_setup_status():
    d = requests.get(f"{BASE_URL}/api/voice/setup", timeout=10).json()
    assert d["steps"] == {"piper_engine": True, "voice": True, "whisper_engine": True, "whisper_model": True}
    assert d["piper"] is True and d["whisper"] is True
    assert len(d["voices"]) >= 1 and len(d["whisper_models"]) >= 1
    assert set(d["manual"]) == {"piper_engine", "voice", "whisper_engine", "whisper_model"}


def test_voice_select_downloaded():
    d = requests.post(f"{BASE_URL}/api/voice/setup/voice", json={"choice": "en_US-lessac-medium"}, timeout=10).json()
    assert d["status"] == "done" and d["log"] == "Already downloaded — selected"


def test_voice_setup_bad_step_and_choice():
    assert requests.post(f"{BASE_URL}/api/voice/setup/bogus", json={}, timeout=10).status_code == 400
    assert requests.post(f"{BASE_URL}/api/voice/setup/voice", json={"choice": "nope"}, timeout=10).status_code == 400


def test_voice_test_wav():
    r = requests.post(f"{BASE_URL}/api/voice/test", json={"text": "Hello from the test"}, timeout=60)
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/wav") and r.content[:4] == b"RIFF"
    assert requests.post(f"{BASE_URL}/api/voice/test", json={"text": ""}, timeout=10).status_code == 422


# Render with voiceover + captions (CPU heavy)
def test_render_voiceover_captions():
    proj = dict(PROJECT, scenes=[dict(s, props={**s["props"], "voiceover": v}) for s, v in zip(PROJECT["scenes"], ["Hello there friend.", "Start today."])])
    job = requests.post(f"{BASE_URL}/api/render", json={"project": proj, "voiceover": True, "captions": True}, timeout=15).json()
    deadline, stages = time.time() + 280, set()
    while time.time() < deadline:
        st = requests.get(f"{BASE_URL}/api/render/{job['id']}", timeout=10).json()
        stages.add(st.get("stage"))
        if st["status"] in ("done", "error", "cancelled"):
            break
        time.sleep(3)
    print("stages", stages)
    assert st["status"] == "done", st
    dl = requests.get(f"{BASE_URL}/api/render/{job['id']}/download", timeout=60)
    assert dl.status_code == 200 and dl.headers["content-type"].startswith("video/mp4") and len(dl.content) > 10000


# Contrast check in Critic
def test_critic_rejects_poor_contrast():
    bad = dict(OUTPUTS, Designer={"primaryColor": "#007BFF", "accentColor": "#FF5733", "background": "#343A40", "font": "Sora"})
    with requests.post(f"{BASE_URL}/api/pipeline/continue", json={"prompt": "Launch film for Orbit", "from_agent": "Director", "outputs": bad}, stream=True, timeout=300) as r:
        assert r.status_code == 200
        evs = events_of(r)
    critic = [e for e in evs if e.get("type") == "agent" and e["name"] == "Critic" and e["status"] == "done"]
    assert critic, [e for e in evs if e.get("type") != "token"][-3:]
    out = critic[0]["output"]
    print("critic", json.dumps(out)[:800])
    assert out["approved"] is False
    assert out["issues"][0].startswith("Rejected colours:")
    assert out["contrast"]["passed"] is False and "primaryColor" in out["contrast"]["palette"]
    brand = evs[-1]["project"]["brand"]
    print("brand", brand)
    assert evs[-1]["type"] == "complete"
    assert brand["primaryColor"].upper() != "#007BFF" and brand["accentColor"].upper() != "#FF5733"
    assert brand["primaryColor"] == out["contrast"]["palette"]["primaryColor"]


# Fast mode (single run)
def test_fast_mode_stream():
    t0 = time.time()
    with requests.post(f"{BASE_URL}/api/pipeline/stream", json={"prompt": "A 10 second launch film for Nimbus, a calm note-taking app", "fast_mode": True}, stream=True, timeout=300) as r:
        evs = events_of(r)
    took = time.time() - t0
    ag = [e for e in evs if e.get("type") == "agent"]
    print("took", took, [(e["name"], e["status"], e.get("model"), e.get("mode"), e.get("elapsed")) for e in ag])
    names = [e["name"] for e in ag if e["status"] == "done"]
    assert names == ["Planner", "Orchestrator + Copywriter", "Designer", "Director"]
    planner = [e for e in ag if e["name"] == "Planner"]
    assert planner[0]["model"] == "rules" and planner[1]["mode"] == "rules"
    assert not any("Critic" in e["name"] for e in ag)
    assert evs[-1]["type"] == "complete" and len(evs[-1]["project"]["scenes"]) == 3
    assert took < 120
