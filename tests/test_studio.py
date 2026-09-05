from __future__ import annotations

import json
from pathlib import Path

from studio import config, db, graph, intake, llm, pages, publisher


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_conversation_roundtrip(studio_env):
    created = db.create_conversation(title="Pilot offer")
    loaded = db.get_conversation(created["id"])
    assert loaded is not None
    assert loaded["id"] == created["id"]
    assert loaded["title"] == "Pilot offer"


def test_missing_key_errors_on_generate(studio_env, monkeypatch, client):
    monkeypatch.setattr(config, "STUDIO_FAKE_LLM", False)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    conversation = client.post("/api/conversations").json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={
            "content": "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call"
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "OPENROUTER_API_KEY" in body["assistant"]["content"]
    assert body["conversation"]["port"] is None
    assert "publisher" not in body["stages_run"]


def test_studio_ui_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.text if response.headers["content-type"].startswith("text/html") else str(response.json())
    assert "Sales Page Studio" in payload or "studio UI" in payload


def test_new_conversation_and_switch(client):
    first = client.post("/api/conversations").json()
    client.post(
        f"/api/conversations/{first['id']}/messages",
        json={"content": "just thinking"},
    )
    second = client.post("/api/conversations").json()
    listed = client.get("/api/conversations").json()
    ids = {item["id"] for item in listed}
    assert first["id"] in ids
    assert second["id"] in ids
    first_detail = client.get(f"/api/conversations/{first['id']}").json()
    second_detail = client.get(f"/api/conversations/{second['id']}").json()
    assert first_detail["messages"][0]["content"] == "just thinking"
    assert second_detail["messages"] == []


def test_restart_restores_messages(studio_env):
    conversation = db.create_conversation()
    db.add_message(conversation["id"], "user", "hello")
    db.add_message(conversation["id"], "assistant", "need offer")
    graph.reset_runtime()
    db.init()
    restored = db.list_conversations()
    messages = db.list_messages(conversation["id"])
    assert restored[0]["id"] == conversation["id"]
    assert [item["content"] for item in messages] == ["hello", "need offer"]


def test_sample_page_uses_editorial_tokens(studio_env):
    sample = json.loads((config.PAGEKIT_DIR / "sample" / "page.json").read_text(encoding="utf-8"))
    site_dir = config.SITES_DIR / "sample"
    pages.write_site(site_dir, sample)
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    css = (site_dir / "tokens.css").read_text(encoding="utf-8")
    assert "--bg: #ffffff" in css
    assert "--text: #0a0a0a" in css
    assert "--font-display" in css
    assert "--accent" in css
    assert "Fraunces" in html
    assert "Source Sans 3" in html
    assert "Close the room" in html


def test_sample_page_has_sales_sections(studio_env):
    sample = json.loads((config.PAGEKIT_DIR / "sample" / "page.json").read_text(encoding="utf-8"))
    site_dir = config.SITES_DIR / "sample"
    pages.write_site(site_dir, sample)
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    for label in ("Sales page", "Problem", "Benefits", "Proof", "Offer", "FAQ", "Call to action"):
        assert label in html
    assert "dashboard" not in html.lower()


def test_graph_runs_stages_in_order(studio_env):
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    assert result["stages_run"] == [
        "intake",
        "copywriter",
        "visual",
        "page_engineer",
        "publisher",
    ]
    assert result.get("copy", {}).get("headline")


def test_follow_up_resumes_same_thread(studio_env):
    conversation = db.create_conversation()
    first = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    second = graph.run_turn(conversation["id"], "Make the headline punchier")
    assert first["slug"] == second["slug"]
    assert first["port"] == second["port"]
    assert "copywriter" in second["stages_run"]
    assert second.get("copy")


def test_incomplete_first_message_does_not_publish(studio_env):
    conversation = db.create_conversation()
    result = graph.run_turn(conversation["id"], "Can you make me a page?")
    assert result["intake_complete"] is False
    assert result.get("port") in (None, "")
    refreshed = db.get_conversation(conversation["id"])
    assert refreshed["port"] is None
    assert refreshed["site_path"] is None


def test_placeholder_visuals_still_publish(studio_env):
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    assert result["visuals"]["images_pending"] is True
    html = Path(db.get_conversation(conversation["id"])["site_path"], "index.html").read_text(
        encoding="utf-8"
    )
    assert "pending" in html.lower()
    assert result.get("preview_url")


def test_site_files_are_isolated(studio_env):
    first = db.create_conversation()
    second = db.create_conversation()
    graph.run_turn(first["id"], "Offer: Alpha\nAudience: A\nCTA: Start")
    graph.run_turn(second["id"], "Offer: Beta\nAudience: B\nCTA: Join")
    one = Path(db.get_conversation(first["id"])["site_path"])
    two = Path(db.get_conversation(second["id"])["site_path"])
    assert one != two
    assert (one / "index.html").exists()
    assert (two / "App.jsx").exists()
    assert "Alpha" in (one / "index.html").read_text(encoding="utf-8")
    assert "Beta" in (two / "index.html").read_text(encoding="utf-8")


def test_two_conversations_get_sequential_ports(studio_env, monkeypatch):
    monkeypatch.setattr(config, "PAGE_PORT_START", 3000)
    first = db.create_conversation()
    second = db.create_conversation()
    one = graph.run_turn(first["id"], "Offer: Alpha\nAudience: A\nCTA: Start")
    two = graph.run_turn(second["id"], "Offer: Beta\nAudience: B\nCTA: Join")
    assert one["port"] == 3000 or publisher.port_is_free(3000) is False
    assert two["port"] != one["port"]
    assert two["port"] > one["port"]
    if one["port"] == 3000:
        assert two["port"] == 3001


def test_rebuild_keeps_port(studio_env):
    conversation = db.create_conversation()
    first = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    second = graph.run_turn(conversation["id"], "Make the headline punchier")
    assert first["port"] == second["port"]
    assert first["preview_url"] == second["preview_url"]


def test_publish_message_includes_new_tab_url(studio_env, client):
    conversation = client.post("/api/conversations").json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"content": "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call"},
    )
    body = response.json()
    url = body["preview_url"]
    assert url.startswith("http://localhost:")
    assert url in body["assistant"]["content"]
    detail = client.get(f"/api/conversations/{conversation['id']}").json()
    assert detail["preview_url"] == url


def test_labeled_intake_parser():
    parsed = intake.parse_labeled_fields("Offer: Tea\nAudience: offices\nCTA: Order")
    assert parsed == {"offer": "Tea", "audience": "offices", "cta": "Order"}
    assert llm.SAMPLE_COPY["headline"]
