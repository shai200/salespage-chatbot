from __future__ import annotations

import json
import subprocess
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
    assert loaded["images_pending"] == 0
    assert loaded.get("next_url") in (None, "")


def test_lead_roundtrip_under_conversation(studio_env):
    conversation = db.create_conversation()
    stored = db.add_lead(
        conversation["id"],
        "demo-slug",
        "Ada Lovelace",
        "ada@example.com",
        "+1 202 555 0147",
    )
    listed = db.list_leads(conversation["id"])
    assert listed[0]["id"] == stored["id"]
    assert listed[0]["conversation_id"] == conversation["id"]
    assert listed[0]["email"] == "ada@example.com"
    assert db.list_leads("missing") == []


def test_public_conversation_includes_images_pending(client):
    created = client.post("/api/conversations").json()
    assert created["images_pending"] is False
    listed = client.get("/api/conversations").json()
    assert listed[0]["images_pending"] is False


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


def test_missing_slug_is_not_a_published_page(client):
    response = client.get("/no-such-page/")
    assert response.status_code == 404


def test_studio_ui_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.text if response.headers["content-type"].startswith("text/html") else str(response.json())
    assert "Homerun" in payload or "studio UI" in payload


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
    assert '<html lang="en">' in html
    assert "<html lang=\"en\" dir=\"rtl\">" not in html


def test_sample_page_has_sales_sections(studio_env):
    sample = json.loads((config.PAGEKIT_DIR / "sample" / "page.json").read_text(encoding="utf-8"))
    site_dir = config.SITES_DIR / "sample"
    pages.write_site(site_dir, sample)
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    for label in (
        "Sales page",
        "Problem",
        "Benefits",
        "Proof",
        "Offer",
        "FAQ",
        "What you get",
        "Discount ends in",
        "Call to action",
    ):
        assert label in html
    assert 'id="lead"' in html
    assert "hidden" in html
    assert 'data-open-lead' in html
    assert 'class="compare-at"' in html
    assert "$2,400" in html
    assert "$970" in html
    assert "data-offer-ends=" in html
    assert "data-unit=" in html
    assert "dashboard" not in html.lower()


def test_turn_events_start_with_intake_then_later_stages(studio_env):
    conversation = db.create_conversation()
    events = list(
        graph.iter_turn_events(
            conversation["id"],
            "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
        )
    )
    progress = [item for item in events if item["type"] == "progress"]
    assert progress[0]["stage"] == "intake"
    assert progress[0]["label"] == "Reading the brief"
    assert [item["stage"] for item in progress] == [
        "intake",
        "copywriter",
        "visual",
        "page_engineer",
        "publisher",
    ]
    assert events[-1]["type"] == "result"
    assert events[-1]["state"]["stages_run"][-1] == "publisher"


def test_message_stream_reports_stages(client):
    conversation = client.post("/api/conversations").json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"content": "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: progress" in response.text
    assert "Reading the brief" in response.text
    assert "Writing the page copy" in response.text
    assert "event: done" in response.text
    assert "http://localhost:" in response.text


def test_reserved_slug_is_not_exact_reserved_name():
    slug = pages.unique_slug("api", "aaaaaaaa-bbbb")
    assert slug != "api"
    assert slug.startswith("page-")


def test_static_publish_uses_origin_slug_url(studio_env, monkeypatch):
    monkeypatch.setattr(config, "PUBLISH_MODE", "static")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://homerun.love")
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    slug = result["slug"]
    assert result["preview_url"] == f"https://homerun.love/{slug}/"
    refreshed = db.get_conversation(conversation["id"])
    assert refreshed["port"] is None
    assert refreshed["pid"] is None
    live = pages.live_site_dir(slug)
    assert (live / "index.html").exists()
    assert not (pages.staging_site_dir(slug) / "index.html").exists()


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


def test_copy_only_skip_does_not_match_instead():
    assert graph._copy_only_follow_up("render the images instead of the placeholders", True) is False
    assert graph._copy_only_follow_up("add the visuals", True) is False
    assert graph._copy_only_follow_up("make the headline punchier", True) is True


def test_follow_up_resumes_same_thread(studio_env):
    conversation = db.create_conversation()
    first = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call\nNext URL: https://cal.example/book",
    )
    site = Path(db.get_conversation(conversation["id"])["site_path"])
    first_page = json.loads((site / "page.json").read_text(encoding="utf-8"))
    first_ends = first_page["offerEndsAt"]
    assert db.get_conversation(conversation["id"])["next_url"] == "https://cal.example/book"
    assert first_page["nextUrl"] == "https://cal.example/book"
    assert first_page["leadModal"]["nextUrl"] == "https://cal.example/book"
    second = graph.run_turn(conversation["id"], "Make the headline punchier")
    assert first["slug"] == second["slug"]
    assert first["port"] == second["port"]
    assert "copywriter" in second["stages_run"]
    assert second.get("copy")
    second_page = json.loads((site / "page.json").read_text(encoding="utf-8"))
    second_ends = second_page["offerEndsAt"]
    assert first_ends == second_ends
    assert second_page["nextUrl"] == "https://cal.example/book"
    assert db.get_conversation(conversation["id"])["next_url"] == "https://cal.example/book"


def test_incomplete_first_message_does_not_publish(studio_env):
    conversation = db.create_conversation()
    result = graph.run_turn(conversation["id"], "Can you make me a page?")
    assert result["intake_complete"] is False
    assert result.get("port") in (None, "")
    refreshed = db.get_conversation(conversation["id"])
    assert refreshed["port"] is None
    assert refreshed["site_path"] is None


TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc``\x00\x00"
    b"\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_placeholder_visuals_still_publish(studio_env):
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    assert result["visuals"]["images_pending"] is True
    assert db.get_conversation(conversation["id"])["images_pending"] == 1
    html = Path(db.get_conversation(conversation["id"])["site_path"], "index.html").read_text(
        encoding="utf-8"
    )
    assert "pending" in html.lower()
    assert result.get("preview_url")


def test_image_success_writes_png(studio_env, monkeypatch):
    monkeypatch.setattr(graph, "fetch_openrouter_images", lambda prompt: [TINY_PNG])
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    site = Path(db.get_conversation(conversation["id"])["site_path"])
    assert result["visuals"]["images_pending"] is False
    assert db.get_conversation(conversation["id"])["images_pending"] == 0
    assert result["visuals"]["hero"]["src"] == "hero.png"
    assert result["visuals"]["dream"]["src"] == "dream.png"
    assert result["visuals"]["risk"]["src"] == "risk.png"
    assert result["visuals"]["value"]["src"] == "value.png"
    for name in ("hero.png", "dream.png", "risk.png", "value.png"):
        assert (site / name).read_bytes() == TINY_PNG
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'src="hero.png"' in html
    assert 'src="dream.png"' in html
    assert 'src="risk.png"' in html
    assert 'src="value.png"' in html


def test_image_api_failure_keeps_placeholders(studio_env, monkeypatch):
    def boom(_prompt):
        raise RuntimeError("gateway 500")

    monkeypatch.setattr(graph, "fetch_openrouter_images", boom)
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    site = Path(db.get_conversation(conversation["id"])["site_path"])
    assert result["visuals"]["images_pending"] is True
    for name in ("hero.png", "dream.png", "risk.png", "value.png"):
        assert not (site / name).exists()
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


def test_published_page_survives_client_restart(studio_env, client):
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    slug = result["slug"]
    first = client.get(f"/{slug}/")
    assert first.status_code == 200
    assert "Launch kit" in first.text
    from fastapi.testclient import TestClient

    from studio.app import app

    with TestClient(app) as restarted:
        again = restarted.get(f"/{slug}/")
        assert again.status_code == 200
        assert "Launch kit" in again.text


def test_rsync_copies_site_when_target_set(studio_env, monkeypatch):
    monkeypatch.setattr(config, "PAGE_RSYNC_TARGET", "user@vps:/var/www/pages")
    monkeypatch.setattr(config, "PAGE_SSH_KEY", "/etc/homerun/ssh/id_ed25519")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://pages.example")
    calls: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(command, **kwargs):
        if command and command[0] == "rsync":
            calls.append(list(command))
            return subprocess.CompletedProcess(command, 0, "", "")
        return real_run(command, **kwargs)

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    slug = result["slug"]
    assert result["preview_url"] == f"https://pages.example/{slug}/"
    assert result.get("error") in (None, "")
    assert calls
    command = calls[0]
    assert command[0] == "rsync"
    assert "-az" in command
    assert "--delete" in command
    assert command[-1] == f"user@vps:/var/www/pages/{slug}/"
    assert "-i" in command[command.index("-e") + 1]


def test_rsync_failure_blocks_publish(studio_env, monkeypatch):
    monkeypatch.setattr(config, "PAGE_RSYNC_TARGET", "user@vps:/var/www/pages")

    real_run = subprocess.run

    def fake_run(command, **kwargs):
        if command and command[0] == "rsync":
            return subprocess.CompletedProcess(command, 1, "", "permission denied")
        return real_run(command, **kwargs)

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    assert "Page copy to VPS failed" in (result.get("error") or "")
    assert "permission denied" in (result.get("assistant_message") or "")


def test_serve_sites_off_does_not_expose_html(studio_env, monkeypatch, client):
    monkeypatch.setattr(config, "SERVE_SITES", False)
    conversation = db.create_conversation()
    result = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    page = client.get(f"/{result['slug']}/")
    assert page.status_code == 404


def test_two_conversations_get_distinct_slug_urls(studio_env, client):
    first = db.create_conversation()
    second = db.create_conversation()
    one = graph.run_turn(first["id"], "Offer: Alpha\nAudience: A\nCTA: Start")
    two = graph.run_turn(second["id"], "Offer: Beta\nAudience: B\nCTA: Join")
    assert one["slug"] != two["slug"]
    assert one["preview_url"] == f"http://localhost:8080/{one['slug']}/"
    assert two["preview_url"] == f"http://localhost:8080/{two['slug']}/"
    page_one = client.get(f"/{one['slug']}/")
    page_two = client.get(f"/{two['slug']}/")
    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert "Alpha" in page_one.text
    assert "Beta" in page_two.text


def test_rebuild_keeps_slug_url(studio_env):
    conversation = db.create_conversation()
    first = graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    second = graph.run_turn(conversation["id"], "Make the headline punchier")
    assert first["slug"] == second["slug"]
    assert first["preview_url"] == second["preview_url"]
    assert first["preview_url"].endswith(f"/{first['slug']}/")


def test_publish_message_includes_new_tab_url(studio_env, client):
    conversation = client.post("/api/conversations").json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"content": "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call"},
    )
    body = response.json()
    url = body["preview_url"]
    assert body["conversation"]["images_pending"] is True
    assert url.startswith("http://localhost:8080/")
    assert url.endswith("/")
    assert url in body["assistant"]["content"]
    page = client.get(f"/{body['conversation']['slug']}/")
    assert page.status_code == 200
    detail = client.get(f"/api/conversations/{conversation['id']}").json()
    assert detail["preview_url"] == url


def test_copywriter_system_prompt_requires_length_and_examples():
    prompt = llm.copywriter_system_prompt()
    assert str(config.COPY_MIN_WORDS) in prompt
    assert "too thin" in prompt.lower()
    assert "density we want" in prompt.lower()
    assert "Ask for the sale ONLY at the very end" in prompt
    assert "AIDA" in prompt
    assert "FOMO" in prompt
    assert "end-dream" in prompt
    assert "valueStack" in prompt
    assert "compareAtPrice" in prompt
    assert "leadModal" in prompt
    assert "Do NOT invent a next URL" in prompt
    assert "4Us" in prompt
    assert "Big Idea" in prompt
    assert "4th-to-5th-grade" in prompt
    assert "Return ONLY a JSON object" in prompt


def test_labeled_intake_parser():
    parsed = intake.parse_labeled_fields("Offer: Tea\nAudience: offices\nCTA: Order")
    assert parsed == {"offer": "Tea", "audience": "offices", "cta": "Order"}
    assert llm.SAMPLE_COPY["headline"]


def test_next_url_intake_keeps_brief_complete_and_drops_javascript():
    labeled = intake.parse_labeled_fields(
        "Offer: Tea\nAudience: offices\nCTA: Order\nNext URL: https://cal.example/book"
    )
    assert labeled["next_url"] == "https://cal.example/book"
    merged = intake.merge_intake({}, labeled)
    assert intake.is_complete(merged) is True
    unsafe = intake.parse_labeled_fields(
        "Offer: Tea\nAudience: offices\nCTA: Order\nNext URL: javascript:alert(1)"
    )
    assert unsafe.get("next_url") == ""
    kept = intake.merge_intake(
        {"offer": "Tea", "audience": "offices", "cta": "Order", "next_url": "https://cal.example/book"},
        {},
    )
    assert kept["next_url"] == "https://cal.example/book"
    rejected = intake.merge_intake(kept, {"next_url": "javascript:alert(1)"})
    assert rejected["next_url"] == ""
    assert intake.is_complete(rejected) is True


def test_detect_language_hebrew_and_english():
    assert pages.detect_language({"language": "he"}) == ("he", "rtl")
    assert pages.detect_language({"headline": "Hello world"}) == ("en", "ltr")
    hebrew = "הצעה לסדנת מכירות לצוותים"
    assert pages.detect_language({}, hebrew) == ("he", "rtl")


def test_hebrew_brief_publishes_rtl_page(studio_env):
    conversation = db.create_conversation()
    graph.run_turn(
        conversation["id"],
        "Offer: סדנת מכירות לצוותים\nAudience: מנהלי מכירות\nCTA: קבעו שיחה",
    )
    site = Path(db.get_conversation(conversation["id"])["site_path"])
    page = json.loads((site / "page.json").read_text(encoding="utf-8"))
    html = (site / "index.html").read_text(encoding="utf-8")
    assert page["language"] == "he"
    assert page["dir"] == "rtl"
    assert '<html lang="he" dir="rtl">' in html
    assert "ההנחה נגמרת בעוד" in html
    assert "הערך המלא" in html
    assert "השאירו פרטים ונמשיך" in html
    assert "אימייל" in html
    assert page["leadModal"]["nameLabel"] == "שם"


def test_english_page_stays_ltr(studio_env):
    conversation = db.create_conversation()
    graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    site = Path(db.get_conversation(conversation["id"])["site_path"])
    html = (site / "index.html").read_text(encoding="utf-8")
    page = json.loads((site / "page.json").read_text(encoding="utf-8"))
    assert '<html lang="en">' in html
    assert "<html lang=\"en\" dir=\"rtl\">" not in html
    assert page["valueStack"]["compareAtPrice"]
    assert page["valueStack"]["price"]
    assert page["offerEndsAt"]
    assert page["countdown"]["endsAt"] == page["offerEndsAt"]
    assert 'class="compare-at"' in html
    assert "data-offer-ends=" in html
    assert "Discount ends in" in html
    assert "querySelector" in html
    assert 'id="lead"' in html
    assert 'data-open-lead' in html
    assert "/api/pages/" in html
    assert page["leadModal"]["slug"] == db.get_conversation(conversation["id"])["slug"]
    assert page.get("nextUrl") == ""


def test_copy_cannot_invent_next_url(studio_env):
    conversation = db.create_conversation()
    graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    db.update_conversation(conversation["id"], next_url="")
    page = pages.page_data_from_copy(
        {**llm.SAMPLE_COPY, "leadModal": {**llm.SAMPLE_COPY["leadModal"], "nextUrl": "https://evil.example"}},
        {},
        {"offer": "Launch kit", "audience": "indie founders", "cta": "Book a call"},
        slug="demo",
        conversation_id=conversation["id"],
        next_url="",
    )
    assert page["nextUrl"] == ""
    assert page["leadModal"]["nextUrl"] == ""


def test_capture_lead_and_isolation(client):
    first = client.post("/api/conversations").json()
    second = client.post("/api/conversations").json()
    first_turn = client.post(
        f"/api/conversations/{first['id']}/messages",
        json={
            "content": "Offer: Kit A\nAudience: founders\nCTA: Book\nNext URL: https://cal.example/a"
        },
    ).json()
    second_turn = client.post(
        f"/api/conversations/{second['id']}/messages",
        json={"content": "Offer: Kit B\nAudience: founders\nCTA: Book"},
    ).json()
    slug_a = first_turn["conversation"]["slug"]
    slug_b = second_turn["conversation"]["slug"]
    ok = client.post(
        f"/api/pages/{slug_a}/leads",
        json={"name": "Ada", "email": "ada@example.com", "phone": "+1 202 555 0147"},
    )
    assert ok.status_code == 200
    assert ok.json()["next_url"] == "https://cal.example/a"
    assert ok.json()["conversation_id"] == first["id"]
    missing_phone = client.post(
        f"/api/pages/{slug_a}/leads",
        json={"name": "Ada", "email": "ada@example.com", "phone": ""},
    )
    assert missing_phone.status_code == 400
    unknown = client.post(
        "/api/pages/no-such-page/leads",
        json={"name": "Ada", "email": "ada@example.com", "phone": "+1 202 555 0147"},
    )
    assert unknown.status_code == 404
    spoof = client.post(
        f"/api/pages/{slug_b}/leads",
        json={
            "name": "Grace",
            "email": "grace@example.com",
            "phone": "+1 202 555 0199",
            "conversation_id": first["id"],
        },
    )
    assert spoof.status_code == 200
    assert spoof.json()["conversation_id"] == second["id"]
    assert spoof.json()["next_url"] is None
    leads_a = client.get(f"/api/conversations/{first['id']}/leads").json()
    leads_b = client.get(f"/api/conversations/{second['id']}/leads").json()
    assert [item["email"] for item in leads_a] == ["ada@example.com"]
    assert [item["email"] for item in leads_b] == ["grace@example.com"]
    html = client.get(f"/{slug_a}/").text
    assert f'/api/pages/' in html
    assert slug_a in html


def test_tokens_cover_lead_modal(studio_env):
    sample = json.loads((config.PAGEKIT_DIR / "sample" / "page.json").read_text(encoding="utf-8"))
    site_dir = config.SITES_DIR / "sample"
    pages.write_site(site_dir, sample)
    css = (site_dir / "tokens.css").read_text(encoding="utf-8")
    assert ".lead-modal" in css
    assert "background: var(--bg)" in css
    assert "color: var(--text)" in css
    assert "var(--accent)" in css
