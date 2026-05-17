from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from anicat_media.api.main import create_app, ctx as runtime_ctx
from anicat_media.api.routers import config as config_router
from anicat_media.api.routers import status as status_router
from anicat_media.core.config import AppConfig
from anicat_media.core.constants import VERSION


class FakeMediaApi:
    def is_connected(self) -> bool:
        return True

    def get_viewer_profile(self):
        return SimpleNamespace(unread_notifications=3)


class FakeLoader:
    def load(self, allow_setup: bool = True):
        return AppConfig()


class FakeCtx:
    def __init__(self, config: AppConfig):
        self.config = config
        self.media_api = FakeMediaApi()
        self._download = None
        self.is_offline = False
        self.data_version = 7
        self._media_api = object()


@pytest.fixture()
def client_and_ctx(monkeypatch):
    app = create_app(config=AppConfig())
    fake_ctx = FakeCtx(AppConfig())
    runtime_ctx._ctx = fake_ctx
    monkeypatch.setattr(config_router, "USER_CONFIG", Path("/tmp/anicat-test-config.toml"))
    monkeypatch.setattr("anicat_media.cli.config.ConfigLoader", FakeLoader)
    monkeypatch.setattr(status_router, "ConfigLoader", FakeLoader)
    monkeypatch.setattr(status_router, "LOG_FILE", str(Path("/tmp/anicat-test.log")))
    monkeypatch.setattr(status_router, "_last_update_check", None)
    monkeypatch.setattr(status_router, "_cached_update_available", False)
    monkeypatch.setattr("anicat_media.utils.subprocess.run_cmd", lambda *args, **kwargs: (0, "", ""))
    try:
        yield TestClient(app), fake_ctx
    finally:
        runtime_ctx._ctx = None


def test_get_config_options(client_and_ctx):
    client, _ = client_and_ctx

    response = client.get("/api/config/options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stream"]["player_type"] == ["embedded", "external"]
    assert payload["stream"]["quality"] == ["1080", "720", "480", "360"]


def test_patch_config_updates_disk_and_runtime(client_and_ctx, tmp_path, monkeypatch):
    client, fake_ctx = client_and_ctx
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_router, "USER_CONFIG", config_path)

    response = client.patch("/api/config/", json={"stream": {"player_type": "external"}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "updated"
    assert payload["config"]["stream"]["player_type"] == "external"
    assert fake_ctx.config.stream.player_type == "external"
    assert "player_type = \"external\"" in config_path.read_text(encoding="utf-8")


def test_health_uses_runtime_ctx_and_loader(client_and_ctx):
    client, _ = client_and_ctx

    response = client.get("/api/status/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_connected"] is True
    assert payload["api_authenticated"] is False
    assert payload["worker_running"] is False
    assert payload["unread_notifications"] == 3
    assert payload["current_version"] == VERSION


def test_logs_tail_reads_requested_lines(client_and_ctx, tmp_path, monkeypatch):
    client, _ = client_and_ctx
    log_path = tmp_path / "anicat.log"
    log_path.write_text("line 1\nline 2\nline 3\nline 4\n", encoding="utf-8")
    monkeypatch.setattr(status_router, "LOG_FILE", str(log_path))

    response = client.get("/api/status/logs?lines=2")

    assert response.status_code == 200
    assert response.json()["logs"].splitlines() == ["line 3", "line 4"]
