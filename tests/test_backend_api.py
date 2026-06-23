from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import _normalize_ufs, app


def test_fastapi_app_health_and_templates() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True}

    templates = client.get("/templates")
    assert templates.status_code == 200
    assert "bussola" in templates.json()["templates"]


def test_normalize_ufs_accepts_lists_and_comma_values() -> None:
    assert _normalize_ufs(["ma, mt", "PA", "MA"]) == ["MA", "MT", "PA"]


def test_normalize_ufs_rejects_invalid_values() -> None:
    with pytest.raises(HTTPException) as exc:
        _normalize_ufs(["MA", "XX"])
    assert exc.value.status_code == 400
