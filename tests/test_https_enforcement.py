from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import create_app


class TestHttpsEnforcement:
    def test_local_env_does_not_redirect_to_https(self, monkeypatch):
        monkeypatch.setattr(settings, "env", "local")
        client = TestClient(create_app())
        resp = client.get("/health", follow_redirects=False)
        assert resp.status_code == 200

    def test_non_local_env_redirects_http_to_https(self, monkeypatch):
        monkeypatch.setattr(settings, "env", "production")
        client = TestClient(create_app(), base_url="http://testserver")
        resp = client.get("/health", follow_redirects=False)
        assert resp.status_code in (301, 307)
        assert resp.headers["location"].startswith("https://")

    def test_non_local_env_sets_hsts_header(self, monkeypatch):
        monkeypatch.setattr(settings, "env", "production")
        client = TestClient(create_app(), base_url="https://testserver")
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "max-age" in resp.headers.get("strict-transport-security", "")
