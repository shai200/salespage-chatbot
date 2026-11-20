from __future__ import annotations

import json
from pathlib import Path

from studio import config

ROOT = Path(__file__).resolve().parent.parent


def test_listen_port_prefers_railway_port():
    assert config.resolve_listen_port({}) == 8080
    assert config.resolve_listen_port({"STUDIO_PORT": "8080"}) == 8080
    assert config.resolve_listen_port({"PORT": "4321", "STUDIO_PORT": "8080"}) == 4321


def test_default_listen_host_stays_loopback():
    assert config.STUDIO_HOST == "127.0.0.1"
    assert config.STUDIO_PORT == 8080


def test_storage_dirs_follow_explicit_env_then_volume(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    monkeypatch.delenv("SITES_DIR", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    assert config.resolve_storage_dir("DATA_DIR", Path("/default/data"), "data") == Path("/default/data")

    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/app/persist")
    assert config.resolve_storage_dir("DATA_DIR", Path("/default/data"), "data") == Path("/app/persist/data")
    assert config.resolve_storage_dir("SITES_DIR", Path("/default/sites"), "sites") == Path("/app/persist/sites")

    monkeypatch.setenv("DATA_DIR", "/elsewhere/data")
    assert config.resolve_storage_dir("DATA_DIR", Path("/default/data"), "data") == Path("/elsewhere/data")


def test_public_origin_prefers_configured_base_over_railway_domain(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://homerun.love")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "homerun.up.railway.app")
    assert config.public_origin() == "https://homerun.love"

    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "")
    assert config.public_origin() == "https://homerun.up.railway.app"

    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    assert config.public_origin() == "http://localhost:8080"


def test_fixture_slug_missing_slug_and_reserved_paths(client, studio_env):
    sites = config.SITES_DIR
    for name in ("api", "assets", "health", "static"):
        planted = sites / name
        planted.mkdir(parents=True)
        (planted / "index.html").write_text(f"<html>planted-{name}</html>", encoding="utf-8")

    staging = sites / ".staging" / "draft"
    staging.mkdir(parents=True)
    (staging / "index.html").write_text("<html>half-written</html>", encoding="utf-8")

    demo = sites / "demo-slug"
    demo.mkdir()
    (demo / "index.html").write_text("<html>fixture-page</html>", encoding="utf-8")
    (demo / "hero.png").write_bytes(b"png-bytes")

    page = client.get("/demo-slug/")
    assert page.status_code == 200
    assert "fixture-page" in page.text
    assert client.get("/demo-slug/hero.png").content == b"png-bytes"

    missing = client.get("/missing-slug/")
    assert missing.status_code == 404
    assert "Homerun" not in missing.text
    assert "fixture-page" not in missing.text

    conversations = client.get("/api/conversations")
    assert conversations.status_code == 200
    assert conversations.json() == []
    assert "planted-api" not in conversations.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "planted-health" not in health.text

    for path in ("/assets/", "/static/", "/static", "/.staging/draft/"):
        response = client.get(path)
        assert "planted-" not in response.text
        assert "half-written" not in response.text
        assert "fixture-page" not in response.text


def test_image_does_not_copy_secrets_or_local_data():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    lowered = dockerfile.lower()
    assert "copy . " not in lowered
    assert ".env" not in dockerfile.split("COPY", 1)[-1] or "COPY" not in dockerfile
    for line in dockerfile.splitlines():
        if line.strip().startswith("COPY"):
            assert ".env" not in line
            assert "kubeconfig" not in line
            assert "sites" not in line.split()
            assert not any(part == "data" for part in line.split())
    for token in (".env", "data", "sites", "civo-love-kubeconfig"):
        assert token in dockerignore
    assert "OPENROUTER_API_KEY=" not in dockerfile


def test_railway_json_is_single_production_service():
    manifest = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://railway.com/railway.schema.json"
    assert manifest["build"]["builder"] == "DOCKERFILE"
    assert manifest["build"]["dockerfilePath"] == "Dockerfile"
    deploy = manifest["deploy"]
    assert deploy["healthcheckPath"] == "/health"
    assert deploy["numReplicas"] == 1
    assert deploy["requiredMountPath"] == "/app/persist"
    assert deploy["overlapSeconds"] == 0
    assert deploy["restartPolicyType"] == "ON_FAILURE"
    assert "environments" not in manifest
    assert "staging" not in json.dumps(manifest).lower()
    assert "OPENROUTER" not in json.dumps(manifest)


def test_nginx_edge_splits_reserved_paths_and_slug_files():
    conf = (ROOT / "deploy" / "nginx-edge.conf").read_text(encoding="utf-8")
    for path in ("/api/", "/assets/", "/static/", "/health"):
        assert path in conf
    assert "proxy_pass http://studio:8080" in conf
    assert "root /app/persist/sites" in conf
    assert "try_files $uri $uri/ $uri/index.html =404" in conf
    assert "/.staging/" in conf
