from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
import urllib.request

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

    def update_list_entry(self, params):
        self.last_update_params = params
        return True

    def delete_list_entry(self, media_id: int):
        self.last_deleted_media_id = media_id
        return True


class FakeMediaRegistry:
    def __init__(self):
        self.updated_entries = []
        self.deleted_media_ids = []

    def update_media_index_entry(self, **kwargs):
        self.updated_entries.append(kwargs)

    def remove_media_record(self, media_id: int):
        self.deleted_media_ids.append(media_id)


class FakeLoader:
    def load(self, allow_setup: bool = True):
        return AppConfig()


class FakeCtx:
    def __init__(self, config: AppConfig):
        self.config = config
        self.media_api = FakeMediaApi()
        self.media_registry = FakeMediaRegistry()
        self._download = None
        self.is_offline = False
        self.data_version = 7
        self._media_api = object()


@pytest.fixture()
def client_and_ctx(monkeypatch):
    app = create_app(config=AppConfig())
    fake_ctx = FakeCtx(AppConfig())
    runtime_ctx._ctx = fake_ctx
    monkeypatch.setattr(
        config_router, "USER_CONFIG", Path("/tmp/anicat-test-config.toml")
    )
    monkeypatch.setattr("anicat_media.cli.config.ConfigLoader", FakeLoader)
    monkeypatch.setattr(status_router, "ConfigLoader", FakeLoader)
    monkeypatch.setattr(status_router, "LOG_FILE", str(Path("/tmp/anicat-test.log")))
    monkeypatch.setattr(status_router, "_last_update_check", None)
    monkeypatch.setattr(status_router, "_cached_update_available", False)
    monkeypatch.setattr(
        "anicat_media.utils.subprocess.run_cmd", lambda *args, **kwargs: (0, "", "")
    )
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

    response = client.patch(
        "/api/config/", json={"stream": {"player_type": "external"}}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "updated"
    assert payload["config"]["stream"]["player_type"] == "external"
    assert fake_ctx.config.stream.player_type == "external"
    assert 'player_type = "external"' in config_path.read_text(encoding="utf-8")


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


def test_health_release_match_does_not_flag_update(client_and_ctx, monkeypatch):
    client, _ = client_and_ctx
    original_exists = status_router.os.path.exists

    def fake_exists(path):
        if str(path).endswith(".git"):
            return False
        return original_exists(path)

    class FakeResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

    def fake_urlopen(*args, **kwargs):
        return FakeResponse({"tag_name": f"v{VERSION}"})

    monkeypatch.setattr(status_router.os.path, "exists", fake_exists)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    response = client.get("/api/status/health")

    assert response.status_code == 200
    assert response.json()["update_available"] is False


def test_check_update_release_match_does_not_flag_update(client_and_ctx, monkeypatch):
    client, _ = client_and_ctx
    original_exists = status_router.os.path.exists

    def fake_exists(path):
        if str(path).endswith(".git"):
            return False
        return original_exists(path)

    class FakeResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

    def fake_urlopen(*args, **kwargs):
        return FakeResponse({"tag_name": f"v{VERSION}"})

    monkeypatch.setattr(status_router.os.path, "exists", fake_exists)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    response = client.post("/api/status/check-update")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["update_available"] is False


def test_trigger_update_clears_cached_update_state(client_and_ctx, monkeypatch):
    client, _ = client_and_ctx
    monkeypatch.setattr(status_router, "_cached_update_available", True)
    monkeypatch.setattr(status_router, "_last_update_check", datetime.now())
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    # Simulate a release install (no .git) so the Darwin release path runs
    monkeypatch.setattr(
        os.path, "exists", lambda p: False if p.endswith("/.git") else True
    )
    monkeypatch.setattr(status_router.subprocess, "Popen", lambda *args, **kwargs: None)

    response = client.post("/api/status/update")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert status_router._cached_update_available is False


def test_user_update_marks_planning_and_increments_version(client_and_ctx, monkeypatch):
    client, fake_ctx = client_and_ctx

    def noop_clear_playback(*args, **kwargs):
        return None

    monkeypatch.setattr(status_router, "clear_playback", noop_clear_playback)

    response = client.post(
        "/api/user/update",
        json={"media_id": 42, "status": "planning"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["synced"] == "pending"
    assert fake_ctx.data_version == 8
    assert fake_ctx.media_registry.updated_entries[-1]["media_id"] == 42
    assert fake_ctx.media_registry.updated_entries[-1]["status"].value == "planning"
    assert fake_ctx.media_api.last_update_params.media_id == 42
    assert fake_ctx.media_api.last_update_params.status.value == "planning"


def test_user_delete_removes_local_entry_and_increments_version(
    client_and_ctx, monkeypatch
):
    client, fake_ctx = client_and_ctx

    def noop_clear_playback(*args, **kwargs):
        return None

    monkeypatch.setattr(status_router, "clear_playback", noop_clear_playback)

    response = client.delete("/api/user/42")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["deleted"] == "pending"
    assert fake_ctx.data_version == 8
    assert fake_ctx.media_registry.deleted_media_ids == [42]
    assert fake_ctx.media_api.last_deleted_media_id == 42


def test_logs_tail_reads_requested_lines(client_and_ctx, tmp_path, monkeypatch):
    client, _ = client_and_ctx
    log_path = tmp_path / "anicat.log"
    log_path.write_text("line 1\nline 2\nline 3\nline 4\n", encoding="utf-8")
    monkeypatch.setattr(status_router, "LOG_FILE", str(log_path))

    response = client.get("/api/status/logs?lines=2")

    assert response.status_code == 200
    assert response.json()["logs"].splitlines() == ["line 3", "line 4"]


def test_hls_proxy_returns_content(client_and_ctx, monkeypatch):
    client, _ = client_and_ctx

    class FakeHttpResponse:
        def __init__(self, text, content, status_code, headers):
            self.text = text
            self.content = content
            self.status_code = status_code
            self.headers = headers

    async def fake_get(*args, **kwargs):
        return FakeHttpResponse(
            text="#EXTM3U\n#EXT-X-STREAM-INF\nsegment.ts",
            content=b"fake-ts-binary-bytes",
            status_code=200,
            headers={"content-type": "video/mp2t"},
        )

    # Monkeypatch the httpx.AsyncClient.get call
    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    # 1. Test m3u8 playlist proxying (should rewrite the content)
    response = client.get(
        "/api/actions/proxy?url=http://example.com/playlist.m3u8&headers=%7B%7D"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-mpegURL"
    assert "/api/actions/proxy" in response.text

    # 2. Test ts segment proxying (should return binary content directly)
    response = client.get(
        "/api/actions/proxy?url=http://example.com/segment.ts&headers=%7B%7D"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp2t"
    assert response.content == b"fake-ts-binary-bytes"
