import json
import os

import requests
from dotenv import load_dotenv


load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def test_ollama_health_contract():
    response = requests.get(f"{BASE_URL}/api/health/ollama", timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["running"], bool)
    assert isinstance(data["models"], list)
    assert isinstance(data["fix"], str)


def test_projects_contract():
    response = requests.get(f"{BASE_URL}/api/projects", timeout=10)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert projects
    assert "_id" not in json.dumps(projects)
    assert {"id", "name", "scene_json"}.issubset(projects[0])


def test_pipeline_stream_contract_and_fast_mode():
    response = requests.post(
        f"{BASE_URL}/api/pipeline/stream",
        json={"prompt": "Create a launch film", "aspect_ratio": "9:16", "fast_mode": True},
        timeout=30,
    )
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "complete"
    assert events[-1]["project"]["aspectRatio"] == "9:16"
    assert any(event.get("name") == "Orchestrator + Planner" for event in events)


def test_render_contract():
    payload = {
        "title": "Test project",
        "aspectRatio": "16:9",
        "brand": {"name": "Test", "primaryColor": "#7CFFCB", "font": "Outfit"},
        "scenes": [{"template": "TextReveal", "durationSec": 2, "props": {"headline": "Hello"}}],
    }
    response = requests.post(f"{BASE_URL}/api/render", json=payload, timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["download_url"] is None
    assert data["estimated_seconds"] >= 4