from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_config_is_not_demo_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert client.get("/config").json() == {"demo": False}


def test_config_reports_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    assert client.get("/config").json() == {"demo": True}


def test_pages_forbid_framing_unless_demo(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    policy = client.get("/app/").headers["content-security-policy"]
    assert "frame-ancestors 'none'" in policy


def test_demo_pages_may_be_framed_by_hugging_face_only(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    policy = client.get("/app/").headers["content-security-policy"]
    assert "frame-ancestors https://huggingface.co https://*.huggingface.co" in policy
    assert "'none'" not in policy.split("frame-ancestors")[1]
    assert "script-src 'self'" in policy
