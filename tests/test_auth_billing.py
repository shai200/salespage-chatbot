from __future__ import annotations

from datetime import datetime, timedelta, timezone

from studio import auth, billing, config, db, pages


def test_user_roundtrip_and_isolation(studio_env):
    alice = db.upsert_user("sub-alice", "alice@example.com", "Alice")
    bob = db.upsert_user("sub-bob", "bob@example.com", "Bob")
    again = db.upsert_user("sub-alice", "alice@example.com", "Alice")
    assert again["id"] == alice["id"]
    db.create_conversation(title="Alice page", user_id=alice["id"])
    db.create_conversation(title="Bob page", user_id=bob["id"])
    assert [row["title"] for row in db.list_conversations(alice["id"])] == ["Alice page"]
    assert [row["title"] for row in db.list_conversations(bob["id"])] == ["Bob page"]


def test_anonymous_me_and_conversations(anon_client):
    me = anon_client.get("/api/me").json()
    assert me["user"] is None
    listed = anon_client.get("/api/conversations")
    assert listed.status_code == 401
    created = anon_client.post("/api/conversations")
    assert created.status_code == 401


def test_google_profile_reuses_user(studio_env, anon_client):
    first = anon_client.post(
        "/auth/fake",
        json={"email": "same@example.com", "name": "Same", "google_sub": "sub-same"},
    ).json()["user"]
    second = anon_client.post(
        "/auth/fake",
        json={"email": "same@example.com", "name": "Same", "google_sub": "sub-same"},
    ).json()["user"]
    assert first["id"] == second["id"]
    assert db.upsert_user("sub-same", "same@example.com")["id"] == first["id"]


def test_cross_user_conversation_is_hidden(studio_env, anon_client):
    anon_client.post(
        "/auth/fake",
        json={"email": "a@example.com", "name": "A", "google_sub": "sub-a"},
    )
    page = anon_client.post("/api/conversations").json()
    anon_client.post("/auth/logout")
    anon_client.post(
        "/auth/fake",
        json={"email": "b@example.com", "name": "B", "google_sub": "sub-b"},
    )
    listed = anon_client.get("/api/conversations").json()
    assert listed == []
    hidden = anon_client.get(f"/api/conversations/{page['id']}")
    assert hidden.status_code == 404
    leads = anon_client.get(f"/api/conversations/{page['id']}/leads")
    assert leads.status_code == 404


def test_health_and_leads_stay_public(client, anon_client):
    assert anon_client.get("/health").status_code == 200
    conversation = client.post("/api/conversations").json()
    from studio import graph

    graph.run_turn(
        conversation["id"],
        "Offer: Launch kit\nAudience: indie founders\nCTA: Book a call",
    )
    row = db.get_conversation(conversation["id"])
    slug = row["slug"]
    page = anon_client.get(f"/{slug}/")
    assert page.status_code == 200
    lead = anon_client.post(
        f"/api/pages/{slug}/leads",
        json={"name": "Ada", "email": "ada@example.com", "phone": "+1 202 555 0147"},
    )
    assert lead.status_code == 200


def test_legacy_owner_claims_unowned_pages(studio_env, anon_client, monkeypatch):
    orphan = db.create_conversation(title="Legacy")
    db.update_conversation(orphan["id"], slug="legacy-page", status="published")
    pages.live_site_dir("legacy-page").mkdir(parents=True, exist_ok=True)
    (pages.live_site_dir("legacy-page") / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    monkeypatch.setattr(config, "HOMERUN_LEGACY_OWNER_EMAIL", "owner@example.com")
    anon_client.post(
        "/auth/fake",
        json={"email": "other@example.com", "name": "Other", "google_sub": "sub-other"},
    )
    assert anon_client.get("/api/conversations").json() == []
    assert anon_client.get("/legacy-page/").status_code == 200
    anon_client.post("/auth/logout")
    anon_client.post(
        "/auth/fake",
        json={"email": "owner@example.com", "name": "Owner", "google_sub": "sub-owner"},
    )
    titles = [row["title"] for row in anon_client.get("/api/conversations").json()]
    assert "Legacy" in titles


def test_fourth_page_requires_card(client):
    for _ in range(3):
        assert client.post("/api/conversations").status_code == 200
    blocked = client.post("/api/conversations")
    assert blocked.status_code == 402
    detail = blocked.json()["detail"]
    assert detail["code"] == "payment_required"
    assert "card" in detail["message"].lower()
    status = client.get("/api/billing/status").json()
    assert status["free_used"] == 3
    assert status["card_required"] is True
    checkout = client.post("/api/billing/checkout").json()
    assert checkout["ready"] is True
    fourth = client.post("/api/conversations")
    assert fourth.status_code == 200


def test_free_pages_have_no_subscription(studio_env, client):
    from studio import graph

    ids = []
    for _ in range(3):
        ids.append(client.post("/api/conversations").json()["id"])
    graph.run_turn(ids[0], "Offer: One\nAudience: buyers\nCTA: Buy")
    assert db.get_page_subscription(ids[0]) is None


def test_extra_page_gets_trial_subscription(studio_env, client):
    from studio import graph

    for _ in range(3):
        client.post("/api/conversations")
    client.post("/api/billing/checkout")
    extra = client.post("/api/conversations").json()
    graph.run_turn(extra["id"], "Offer: Extra\nAudience: buyers\nCTA: Buy")
    sub = db.get_page_subscription(extra["id"])
    assert sub is not None
    assert sub["status"] == "trialing"
    assert sub["trial_end"]


def test_webhook_unpublish_and_restore(studio_env, client):
    from studio import graph

    for _ in range(3):
        client.post("/api/conversations")
    client.post("/api/billing/checkout")
    extra = client.post("/api/conversations").json()
    graph.run_turn(extra["id"], "Offer: Extra\nAudience: buyers\nCTA: Buy")
    row = db.get_conversation(extra["id"])
    slug = row["slug"]
    db.upsert_page_subscription(
        row["user_id"],
        extra["id"],
        stripe_subscription_id="sub_extra",
        status="trialing",
        trial_end=row.get("created_at"),
    )
    started = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    db.upsert_page_subscription(
        row["user_id"],
        extra["id"],
        stripe_subscription_id="sub_extra",
        status="unpaid",
        grace_started_at=started,
    )
    client.post(
        "/api/billing/stripe/webhook",
        json={
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_extra"}},
        },
    )
    assert client.get(f"/{slug}/").status_code == 404
    assert db.get_conversation(extra["id"])["status"] == "unpublished"
    client.post(
        "/api/billing/stripe/webhook",
        json={
            "type": "invoice.paid",
            "data": {"object": {"subscription": "sub_extra", "status": "active"}},
        },
    )
    assert client.get(f"/{slug}/").status_code == 200
    assert db.get_conversation(extra["id"])["status"] == "published"


def test_failed_extra_invoice_leaves_free_pages_up(studio_env, client):
    from studio import graph

    first = client.post("/api/conversations").json()
    graph.run_turn(first["id"], "Offer: Free\nAudience: buyers\nCTA: Buy")
    free_slug = db.get_conversation(first["id"])["slug"]
    client.post("/api/conversations")
    client.post("/api/conversations")
    client.post("/api/billing/checkout")
    extra = client.post("/api/conversations").json()
    graph.run_turn(extra["id"], "Offer: Extra\nAudience: buyers\nCTA: Buy")
    extra_row = db.get_conversation(extra["id"])
    db.upsert_page_subscription(
        extra_row["user_id"],
        extra["id"],
        stripe_subscription_id="sub_fail",
        status="unpaid",
        grace_started_at=(datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
    )
    billing.handle_stripe_event(
        {"type": "invoice.payment_failed", "data": {"object": {"subscription": "sub_fail"}}},
        now=datetime.now(timezone.utc),
    )
    assert client.get(f"/{free_slug}/").status_code == 200
    assert auth.public_user(db.get_user(extra_row["user_id"]))["email"]


def test_logout_rejects_list(client):
    client.post("/auth/logout")
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/me").json()["user"] is None
