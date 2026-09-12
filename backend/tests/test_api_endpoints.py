"""Integration tests for FastAPI endpoints."""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    print("Health check response:", data)
    assert data["status"] == "ready"


def test_presets():
    res = client.get("/api/presets")
    assert res.status_code == 200
    presets = res.json()
    print(f"Loaded {len(presets['genres'])} genres, {len(presets['voices'])} voices, {len(presets['aspect_ratios'])} aspect ratios.")
    assert len(presets["genres"]) >= 4
    assert len(presets["voices"]) >= 3


def test_generate_and_verify_hooks():
    payload = {
        "topic": "The Voynich Manuscript",
        "genre": "dark_mystery",
        "target_audience": "Mystery buffs",
        "aspect_ratio": "9:16",
        "min_pass_score": 80,
        "max_iterations": 2
    }
    res = client.post("/api/hooks/generate-and-verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    print("Hook Generation & Verification Result:")
    print(f"  Iterations: {data['total_iterations']}")
    print(f"  Winning Hook: {data['winning_hook']['text']}")
    print(f"  Evaluation Total Score: {data['winning_evaluation']['total_score']}/100")
    print(f"  Strengths: {data['winning_evaluation']['strengths']}")
    assert data["winning_hook"] is not None
    assert data["winning_evaluation"]["total_score"] >= 80


def test_generate_script():
    payload = {
        "topic": "The Voynich Manuscript",
        "genre": "dark_mystery",
        "aspect_ratio": "9:16",
        "target_duration_sec": 30
    }
    res = client.post("/api/scripts/generate", json=payload)
    assert res.status_code == 200
    script = res.json()
    print(f"Generated Script: '{script['title']}' with {len(script['scenes'])} scenes.")
    for sc in script["scenes"]:
        print(f"  Scene {sc['scene_id']}: [{sc['on_screen_text']}] -> {sc['visual_hook_type']}")
    assert len(script["scenes"]) >= 4


if __name__ == "__main__":
    test_health()
    test_presets()
    test_generate_and_verify_hooks()
    test_generate_script()
    print("\nAll FastAPI Endpoint tests succeeded!")
