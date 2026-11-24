from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_config_is_not_demo_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert client.get("/config").json() == {"demo": False}


def test_config_reports_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    assert client.get("/config").json() == {"demo": True}
