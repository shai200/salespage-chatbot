from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from studio import config, db, pages


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fake() -> bool:
    return config.STUDIO_FAKE_AUTH or not config.STRIPE_SECRET_KEY


def has_payment_method(user: dict[str, Any]) -> bool:
    return bool(user.get("payment_method_ok"))


def checkout_url(user: dict[str, Any], origin: str) -> str | None:
    if _fake():
        return None
    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(email=user.get("email"), metadata={"user_id": user["id"]})
        customer_id = customer.id
        db.update_user(user["id"], stripe_customer_id=customer_id)
    session = stripe.checkout.Session.create(
        mode="setup",
        customer=customer_id,
        success_url=f"{origin}/?billing=ready",
        cancel_url=f"{origin}/?billing=cancel",
        metadata={"user_id": user["id"]},
    )
    return session.url


def mark_payment_method(user_id: str) -> None:
    db.update_user(user_id, payment_method_ok=1)


def start_checkout(user: dict[str, Any], origin: str) -> dict[str, Any]:
    if _fake():
        mark_payment_method(user["id"])
        return {"url": None, "ready": True}
    url = checkout_url(user, origin)
    return {"url": url, "ready": False}


def create_blocked_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": "payment_required",
        "message": "A card is required to create another page.",
        "checkout_url": None,
        "free_used": min(db.count_conversations(user["id"]), config.FREE_PAGE_LIMIT),
        "free_limit": config.FREE_PAGE_LIMIT,
    }


def status_payload(user: dict[str, Any]) -> dict[str, Any]:
    used = db.count_conversations(user["id"])
    card = has_payment_method(user)
    required = used >= config.FREE_PAGE_LIMIT and not card
    return {
        "free_used": min(used, config.FREE_PAGE_LIMIT),
        "free_limit": config.FREE_PAGE_LIMIT,
        "page_count": used,
        "has_payment_method": card,
        "card_required": required,
    }


def ensure_extra_subscription(conversation: dict[str, Any]) -> dict[str, Any] | None:
    if not conversation.get("user_id") or not db.is_extra_page(conversation):
        return None
    existing = db.get_page_subscription(conversation["id"])
    if existing:
        return existing
    trial_end = (_now() + timedelta(days=365)).isoformat()
    stripe_sub_id = None
    if not _fake():
        import stripe

        stripe.api_key = config.STRIPE_SECRET_KEY
        user = db.get_user(conversation["user_id"])
        if not user:
            return None
        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.get("email"), metadata={"user_id": user["id"]}
            )
            customer_id = customer.id
            db.update_user(user["id"], stripe_customer_id=customer_id)
        created = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": config.STRIPE_PAGE_ANNUAL_PRICE_ID}],
            trial_end=int((_now() + timedelta(days=365)).timestamp()),
            metadata={"conversation_id": conversation["id"], "user_id": user["id"]},
        )
        stripe_sub_id = created.id
    return db.upsert_page_subscription(
        conversation["user_id"],
        conversation["id"],
        stripe_subscription_id=stripe_sub_id,
        status="trialing",
        trial_end=trial_end,
    )


def grace_expired(sub: dict[str, Any], now: datetime | None = None) -> bool:
    started = _parse_time(sub.get("grace_started_at"))
    if not started:
        return False
    when = now or _now()
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return when >= started + timedelta(days=config.BILLING_GRACE_DAYS)


def unpublish(conversation_id: str) -> None:
    db.update_conversation(conversation_id, status="unpublished")


def restore(conversation_id: str) -> None:
    row = db.get_conversation(conversation_id)
    if not row:
        return
    slug = row.get("slug") or ""
    if slug and (pages.live_site_dir(slug) / "index.html").is_file():
        db.update_conversation(conversation_id, status="published")


def is_publicly_served(conversation: dict[str, Any] | None, now: datetime | None = None) -> bool:
    if not conversation:
        return False
    slug = conversation.get("slug") or ""
    if not slug or not (pages.live_site_dir(slug) / "index.html").is_file():
        return False
    if conversation.get("status") == "unpublished":
        return False
    sub = db.get_page_subscription(conversation["id"])
    if sub and sub.get("status") == "unpaid" and grace_expired(sub, now=now):
        unpublish(conversation["id"])
        return False
    return True


def handle_stripe_event(event: dict[str, Any], now: datetime | None = None) -> None:
    kind = event.get("type") or ""
    data = (event.get("data") or {}).get("object") or {}
    if kind == "checkout.session.completed":
        user_id = (data.get("metadata") or {}).get("user_id")
        if user_id:
            mark_payment_method(user_id)
        return
    if kind in {"invoice.paid", "customer.subscription.updated"}:
        sub_id = data.get("subscription") or data.get("id")
        status = data.get("status") or "active"
        if kind == "invoice.paid":
            status = "active"
        sub = db.get_page_subscription_by_stripe_id(str(sub_id or ""))
        if not sub and data.get("metadata", {}).get("conversation_id"):
            sub = db.get_page_subscription(data["metadata"]["conversation_id"])
        if not sub:
            return
        if status in {"active", "trialing"}:
            db.upsert_page_subscription(
                sub["user_id"],
                sub["conversation_id"],
                stripe_subscription_id=sub.get("stripe_subscription_id"),
                status=status,
                grace_started_at=None,
            )
            restore(sub["conversation_id"])
        return
    if kind == "invoice.payment_failed":
        sub_id = data.get("subscription")
        sub = db.get_page_subscription_by_stripe_id(str(sub_id or ""))
        if not sub:
            return
        started = sub.get("grace_started_at") or (now or _now()).isoformat()
        db.upsert_page_subscription(
            sub["user_id"],
            sub["conversation_id"],
            stripe_subscription_id=sub.get("stripe_subscription_id"),
            status="unpaid",
            grace_started_at=started,
        )
        if grace_expired(
            db.get_page_subscription(sub["conversation_id"]) or {},
            now=now,
        ):
            unpublish(sub["conversation_id"])
