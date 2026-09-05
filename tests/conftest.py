from __future__ import annotations

import pytest

from studio import config, db, graph, publisher


@pytest.fixture
def studio_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "data" / "studio.sqlite")
    monkeypatch.setattr(config, "SITES_DIR", tmp_path / "sites")
    monkeypatch.setattr(config, "STUDIO_FAKE_LLM", True)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(config, "PAGE_RSYNC_TARGET", "")
    monkeypatch.setattr(config, "PAGE_SSH_KEY", "")
    monkeypatch.setattr(config, "SERVE_SITES", True)
    graph.reset_runtime()
    db.init()
    yield {
        "tmp": tmp_path,
        "config": config,
        "db": db,
        "graph": graph,
        "publisher": publisher,
    }
    publisher.shutdown_all()
    graph.reset_runtime()


@pytest.fixture
def client(studio_env):
    from fastapi.testclient import TestClient

    from studio.app import app

    with TestClient(app) as test_client:
        yield test_client
