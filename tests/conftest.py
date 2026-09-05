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
    monkeypatch.setattr(config, "STUDIO_FAKE_AUTH", True)
    monkeypatch.setattr(config, "SESSION_SECRET", "test-session-secret")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "test-google-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "test-google-secret")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.setattr(config, "STRIPE_PAGE_ANNUAL_PRICE_ID", "price_test")
    monkeypatch.setattr(config, "HOMERUN_LEGACY_OWNER_EMAIL", "")
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


def _make_client():
    from fastapi.testclient import TestClient

    from studio.app import app

    return TestClient(app)


@pytest.fixture
def anon_client(studio_env):
    with _make_client() as test_client:
        yield test_client


@pytest.fixture
def client(studio_env):
    with _make_client() as test_client:
        test_client.post(
            "/auth/fake",
            json={
                "email": "tester@example.com",
                "name": "Tester",
                "google_sub": "google-sub-tester",
            },
        )
        yield test_client
