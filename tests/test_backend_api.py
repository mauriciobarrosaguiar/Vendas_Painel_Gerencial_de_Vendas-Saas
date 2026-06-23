from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_fastapi_app_health_and_templates() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True}

    templates = client.get("/templates")
    assert templates.status_code == 200
    assert "bussola" in templates.json()["templates"]
