from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from studio import config
from studio.intake import sanitize_next_url

SECTION_IMPORTS = (
    "Hero",
    "Problem",
    "Benefits",
    "Proof",
    "Offer",
    "FAQ",
    "ValueStack",
    "OfferCountdown",
    "FinalCTA",
    "LeadModal",
    "Footer",
)

OFFER_WINDOW = timedelta(hours=24)

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def _collect_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_collect_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_collect_text(item) for item in value)
    return str(value or "")


def detect_language(copy: dict[str, Any], extras: str = "") -> tuple[str, str]:
    explicit = str((copy or {}).get("language") or "").strip().lower()
    if explicit in {"he", "hebrew", "iw"}:
        return "he", "rtl"
    blob = f"{_collect_text(copy)} {extras}"
    if len(HEBREW_RE.findall(blob)) >= 5:
        return "he", "rtl"
    return "en", "ltr"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "sales-page"


def unique_slug(base: str, conversation_id: str) -> str:
    head = slugify(base)[:40]
    if head in config.RESERVED_SLUGS:
        head = f"page-{head}"
    slug = f"{head}-{conversation_id[:8]}"
    if slug in config.RESERVED_SLUGS:
        slug = f"page-{conversation_id[:8]}"
    return slug


def staging_site_dir(slug: str) -> Path:
    return config.SITES_DIR / ".staging" / slug


def live_site_dir(slug: str) -> Path:
    return config.SITES_DIR / slug


def promote_staged_site(slug: str) -> Path:
    staging = staging_site_dir(slug)
    live = live_site_dir(slug)
    if (staging / "index.html").exists():
        live.parent.mkdir(parents=True, exist_ok=True)
        previous = config.SITES_DIR / ".staging" / f"{slug}.old"
        if previous.exists():
            shutil.rmtree(previous)
        if live.exists():
            live.replace(previous)
        staging.replace(live)
        if previous.exists():
            shutil.rmtree(previous, ignore_errors=True)
        return live
    if (live / "index.html").exists():
        return live
    raise RuntimeError(f"Cannot publish {slug}: index.html is missing")


def _jsx_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def _jsx_bool(value: Any) -> str:
    return "true" if value else "false"


def fresh_offer_ends_at() -> str:
    return (datetime.now(timezone.utc) + OFFER_WINDOW).isoformat()


def resolve_offer_ends_at(slug: str = "") -> str:
    if slug:
        for path in (live_site_dir(slug) / "page.json", staging_site_dir(slug) / "page.json"):
            if not path.exists():
                continue
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("offerEndsAt")
            except (OSError, json.JSONDecodeError):
                continue
            if existing:
                return str(existing)
    return fresh_offer_ends_at()


def countdown_parts(ends_at: str) -> tuple[int, int, int]:
    try:
        end = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
    except ValueError:
        return 24, 0, 0
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    remaining = max(0, int((end - datetime.now(timezone.utc)).total_seconds()))
    hours, rem = divmod(remaining, 3600)
    minutes, seconds = divmod(rem, 60)
    return hours, minutes, seconds


def lead_modal_labels(language: str) -> dict[str, str]:
    if language == "he":
        return {
            "heading": "השאירו פרטים ונמשיך",
            "nameLabel": "שם",
            "emailLabel": "אימייל",
            "phoneLabel": "טלפון",
            "buttonLabel": "שלחו",
            "thanks": "קיבלנו. תודה.",
            "errorLabel": "בדקו את השדות ונסו שוב.",
        }
    return {
        "heading": "Leave your details and we will take it from here",
        "nameLabel": "Name",
        "emailLabel": "Email",
        "phoneLabel": "Phone",
        "buttonLabel": "Send",
        "thanks": "Got it. Thank you.",
        "errorLabel": "Check the fields and try again.",
    }


def lead_modal_from_copy(
    copy: dict[str, Any],
    language: str,
    slug: str,
    conversation_id: str,
    next_url: str,
) -> dict[str, Any]:
    labels = lead_modal_labels(language)
    raw = copy.get("leadModal") or {}
    cta_label = (copy.get("cta") or {}).get("label") or labels["buttonLabel"]
    heading = str(raw.get("heading") or labels["heading"]).strip()
    button = str(raw.get("buttonLabel") or cta_label or labels["buttonLabel"]).strip()
    thanks = str(raw.get("thanks") or labels["thanks"]).strip()
    if language == "he":
        if not HEBREW_RE.search(heading):
            heading = labels["heading"]
        if not HEBREW_RE.search(button):
            button = labels["buttonLabel"]
        if not HEBREW_RE.search(thanks):
            thanks = labels["thanks"]
    return {
        "heading": heading,
        "nameLabel": labels["nameLabel"],
        "emailLabel": labels["emailLabel"],
        "phoneLabel": labels["phoneLabel"],
        "buttonLabel": button,
        "thanks": thanks,
        "errorLabel": labels["errorLabel"],
        "slug": slug,
        "conversationId": conversation_id,
        "nextUrl": sanitize_next_url(next_url),
    }


def close_labels(language: str) -> dict[str, str]:
    if language == "he":
        return {
            "stackLabel": "הערך המלא",
            "totalLabel": "שווי כולל",
            "bonusLabel": "בונוס",
            "countdownLabel": "ההנחה נגמרת בעוד",
            "expiredLabel": "ההנחה נגמרה",
            "hoursLabel": "שעות",
            "minutesLabel": "דקות",
            "secondsLabel": "שניות",
        }
    return {
        "stackLabel": "What you get",
        "totalLabel": "Total value",
        "bonusLabel": "Bonus",
        "countdownLabel": "Discount ends in",
        "expiredLabel": "This discount has ended",
        "hoursLabel": "Hours",
        "minutesLabel": "Minutes",
        "secondsLabel": "Seconds",
    }


def value_stack_from_copy(copy: dict[str, Any], intake: dict[str, str]) -> dict[str, Any]:
    raw = copy.get("valueStack") or {}
    items = []
    for item in raw.get("items") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or "").strip()
        if not name:
            continue
        items.append(
            {
                "name": name,
                "worth": str(item.get("worth") or item.get("value") or "").strip(),
                "bonus": bool(item.get("bonus")),
            }
        )
    price = str(raw.get("price") or (copy.get("offer") or {}).get("price") or "").strip()
    if not items and (intake.get("offer") or price):
        items = [
            {
                "name": intake.get("offer") or "Core offer",
                "worth": price or "Included",
                "bonus": False,
            }
        ]
    return {
        "title": str(raw.get("title") or "").strip(),
        "items": items,
        "totalWorth": str(raw.get("totalWorth") or "").strip(),
        "compareAtPrice": str(raw.get("compareAtPrice") or "").strip(),
        "price": price,
    }


def _write_app_jsx(site_dir: Path, data: dict[str, Any]) -> None:
    hero = data.get("hero", {})
    problem = data.get("problem", {})
    benefits = data.get("benefits", [])
    benefit_visual = data.get("benefitVisual", {})
    proof = data.get("proof", [])
    offer = data.get("offer", {})
    faq = data.get("faq", [])
    stack = data.get("valueStack", {})
    countdown = data.get("countdown", {})
    cta = data.get("cta", {})
    lead_modal = data.get("leadModal", {})
    footer = data.get("footer", "")

    benefit_items = ",\n    ".join(
        f"{{ title: {_jsx_string(item.get('title'))}, body: {_jsx_string(item.get('body'))} }}"
        for item in benefits
    )
    proof_items = ",\n    ".join(
        f"{{ quote: {_jsx_string(item.get('quote'))}, name: {_jsx_string(item.get('name'))} }}"
        for item in proof
    )
    faq_items = ",\n    ".join(
        f"{{ q: {_jsx_string(item.get('q'))}, a: {_jsx_string(item.get('a'))} }}"
        for item in faq
    )
    stack_items = ",\n    ".join(
        f"{{ name: {_jsx_string(item.get('name'))}, worth: {_jsx_string(item.get('worth'))}, bonus: {_jsx_bool(item.get('bonus'))} }}"
        for item in stack.get("items") or []
    )

    source = f"""import React from "react";
import {{ {", ".join(SECTION_IMPORTS)} }} from "./sections.jsx";

const page = {{
  hero: {{
    headline: {_jsx_string(hero.get("headline"))},
    accent: {_jsx_string(hero.get("accent"))},
    subheadline: {_jsx_string(hero.get("subheadline"))},
    ctaLabel: {_jsx_string(hero.get("ctaLabel"))},
    visualLabel: {_jsx_string(hero.get("visualLabel"))},
    src: {_jsx_string(hero.get("src"))},
  }},
  problem: {{
    title: {_jsx_string(problem.get("title"))},
    body: {_jsx_string(problem.get("body"))},
    visualLabel: {_jsx_string(problem.get("visualLabel"))},
    src: {_jsx_string(problem.get("src"))},
  }},
  benefits: [
    {benefit_items}
  ],
  benefitVisual: {{
    visualLabel: {_jsx_string(benefit_visual.get("visualLabel"))},
    src: {_jsx_string(benefit_visual.get("src"))},
  }},
  proof: [
    {proof_items}
  ],
  offer: {{
    title: {_jsx_string(offer.get("title"))},
    body: {_jsx_string(offer.get("body"))},
    price: {_jsx_string(offer.get("price"))},
    ctaLabel: {_jsx_string(offer.get("ctaLabel"))},
    visualLabel: {_jsx_string(offer.get("visualLabel"))},
    src: {_jsx_string(offer.get("src"))},
  }},
  faq: [
    {faq_items}
  ],
  valueStack: {{
    title: {_jsx_string(stack.get("title"))},
    items: [
    {stack_items}
    ],
    totalWorth: {_jsx_string(stack.get("totalWorth"))},
    compareAtPrice: {_jsx_string(stack.get("compareAtPrice"))},
    price: {_jsx_string(stack.get("price"))},
    label: {_jsx_string(stack.get("label"))},
    totalLabel: {_jsx_string(stack.get("totalLabel"))},
    bonusLabel: {_jsx_string(stack.get("bonusLabel"))},
  }},
  countdown: {{
    endsAt: {_jsx_string(countdown.get("endsAt"))},
    hours: {_jsx_string(countdown.get("hours"))},
    minutes: {_jsx_string(countdown.get("minutes"))},
    seconds: {_jsx_string(countdown.get("seconds"))},
    label: {_jsx_string(countdown.get("label"))},
    expiredLabel: {_jsx_string(countdown.get("expiredLabel"))},
    hoursLabel: {_jsx_string(countdown.get("hoursLabel"))},
    minutesLabel: {_jsx_string(countdown.get("minutesLabel"))},
    secondsLabel: {_jsx_string(countdown.get("secondsLabel"))},
  }},
  cta: {{
    text: {_jsx_string(cta.get("text"))},
    label: {_jsx_string(cta.get("label"))},
  }},
  leadModal: {{
    heading: {_jsx_string(lead_modal.get("heading"))},
    nameLabel: {_jsx_string(lead_modal.get("nameLabel"))},
    emailLabel: {_jsx_string(lead_modal.get("emailLabel"))},
    phoneLabel: {_jsx_string(lead_modal.get("phoneLabel"))},
    buttonLabel: {_jsx_string(lead_modal.get("buttonLabel"))},
    thanks: {_jsx_string(lead_modal.get("thanks"))},
    errorLabel: {_jsx_string(lead_modal.get("errorLabel"))},
    slug: {_jsx_string(lead_modal.get("slug"))},
  }},
  footer: {_jsx_string(footer)},
}};

export default function App() {{
  return (
    <main className="page">
      <Hero {{...page.hero}} />
      <Problem {{...page.problem}} />
      <Benefits items={{page.benefits}} {{...page.benefitVisual}} />
      <Proof items={{page.proof}} />
      <Offer {{...page.offer}} />
      <FAQ items={{page.faq}} />
      <ValueStack {{...page.valueStack}} />
      <OfferCountdown {{...page.countdown}} />
      <FinalCTA {{...page.cta}} />
      <LeadModal {{...page.leadModal}} />
      <Footer text={{page.footer}} />
    </main>
  );
}}
"""
    (site_dir / "App.jsx").write_text(source, encoding="utf-8")


def page_data_from_copy(
    copy: dict[str, Any],
    visuals: dict[str, Any],
    intake: dict[str, str],
    user_message: str = "",
    slug: str = "",
    conversation_id: str = "",
    next_url: str = "",
) -> dict[str, Any]:
    cta_label = (copy.get("cta") or {}).get("label") or intake.get("cta") or "Get started"
    extras = " ".join(
        [
            user_message,
            intake.get("offer") or "",
            intake.get("audience") or "",
            intake.get("cta") or "",
        ]
    )
    language, direction = detect_language(copy, extras)
    labels = close_labels(language)
    stack = value_stack_from_copy(copy, intake)
    ends_at = resolve_offer_ends_at(slug)
    hours, minutes, seconds = countdown_parts(ends_at)
    return {
        "title": copy.get("headline") or intake.get("offer") or "Sales page",
        "language": language,
        "dir": direction,
        "hero": {
            "headline": copy.get("headline") or intake.get("offer"),
            "accent": copy.get("headline_accent") or "",
            "subheadline": copy.get("subheadline") or "",
            "ctaLabel": cta_label,
            "visualLabel": (visuals.get("hero") or {}).get("label") or "Visual pending",
            "src": (visuals.get("hero") or {}).get("src") or "",
        },
        "problem": {
            **(copy.get("problem") or {"title": "", "body": ""}),
            "visualLabel": (visuals.get("risk") or {}).get("label") or "",
            "src": (visuals.get("risk") or {}).get("src") or "",
        },
        "benefits": copy.get("benefits") or [],
        "benefitVisual": {
            "visualLabel": (visuals.get("dream") or {}).get("label") or "",
            "src": (visuals.get("dream") or {}).get("src") or "",
        },
        "proof": copy.get("proof") or [],
        "offer": {
            **(copy.get("offer") or {}),
            "ctaLabel": cta_label,
            "visualLabel": (visuals.get("value") or {}).get("label") or "",
            "src": (visuals.get("value") or {}).get("src") or "",
        },
        "faq": copy.get("faq") or [],
        "valueStack": {
            **stack,
            "label": labels["stackLabel"],
            "totalLabel": labels["totalLabel"],
            "bonusLabel": labels["bonusLabel"],
        },
        "countdown": {
            "endsAt": ends_at,
            "hours": f"{hours:02d}",
            "minutes": f"{minutes:02d}",
            "seconds": f"{seconds:02d}",
            "label": labels["countdownLabel"],
            "expiredLabel": labels["expiredLabel"],
            "hoursLabel": labels["hoursLabel"],
            "minutesLabel": labels["minutesLabel"],
            "secondsLabel": labels["secondsLabel"],
        },
        "offerEndsAt": ends_at,
        "cta": copy.get("cta") or {"label": cta_label, "text": ""},
        "leadModal": lead_modal_from_copy(
            copy,
            language,
            slug,
            conversation_id,
            next_url,
        ),
        "nextUrl": sanitize_next_url(next_url),
        "conversationId": conversation_id,
        "footer": copy.get("footer") or "Generated with Homerun Sales Page Builder.",
        "images_pending": bool(visuals.get("images_pending", True)),
    }


def _with_close(page_data: dict[str, Any], slug: str = "") -> dict[str, Any]:
    data = dict(page_data)
    language = str(data.get("language") or "en")
    labels = close_labels(language)
    ends_at = (
        data.get("offerEndsAt")
        or (data.get("countdown") or {}).get("endsAt")
        or resolve_offer_ends_at(slug)
    )
    hours, minutes, seconds = countdown_parts(str(ends_at))
    stack = dict(data.get("valueStack") or {})
    stack.setdefault("items", [])
    stack.setdefault("label", labels["stackLabel"])
    stack.setdefault("totalLabel", labels["totalLabel"])
    stack.setdefault("bonusLabel", labels["bonusLabel"])
    data["valueStack"] = stack
    data["offerEndsAt"] = ends_at
    countdown = dict(data.get("countdown") or {})
    countdown["endsAt"] = ends_at
    countdown.setdefault("hours", f"{hours:02d}")
    countdown.setdefault("minutes", f"{minutes:02d}")
    countdown.setdefault("seconds", f"{seconds:02d}")
    countdown.setdefault("label", labels["countdownLabel"])
    countdown.setdefault("expiredLabel", labels["expiredLabel"])
    countdown.setdefault("hoursLabel", labels["hoursLabel"])
    countdown.setdefault("minutesLabel", labels["minutesLabel"])
    countdown.setdefault("secondsLabel", labels["secondsLabel"])
    data["countdown"] = countdown
    modal = dict(data.get("leadModal") or {})
    labels = lead_modal_labels(language)
    modal.setdefault("heading", labels["heading"])
    modal.setdefault("nameLabel", labels["nameLabel"])
    modal.setdefault("emailLabel", labels["emailLabel"])
    modal.setdefault("phoneLabel", labels["phoneLabel"])
    modal.setdefault("buttonLabel", labels["buttonLabel"])
    modal.setdefault("thanks", labels["thanks"])
    modal.setdefault("errorLabel", labels["errorLabel"])
    modal.setdefault("slug", slug)
    data["leadModal"] = modal
    if "nextUrl" in data:
        data["nextUrl"] = sanitize_next_url(str(data.get("nextUrl") or ""))
    return data


def write_site(site_dir: Path, page_data: dict[str, Any]) -> None:
    page_data = _with_close(page_data, site_dir.name)
    site_dir.mkdir(parents=True, exist_ok=True)
    kit_src = config.PAGEKIT_DIR / "src"
    shutil.copy2(kit_src / "tokens.css", site_dir / "tokens.css")
    shutil.copy2(kit_src / "sections.jsx", site_dir / "sections.jsx")
    (site_dir / "page.json").write_text(
        json.dumps(page_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_app_jsx(site_dir, page_data)
    prerender(site_dir, page_data)


def prerender(site_dir: Path, page_data: dict[str, Any]) -> Path:
    script = config.PAGEKIT_DIR / "prerender.mjs"
    result = subprocess.run(
        ["node", str(script), str(site_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to prerender sales page: {result.stderr or result.stdout}"
        )
    index = site_dir / "index.html"
    if not index.exists():
        raise RuntimeError("Prerender finished without writing index.html")
    # Title fallback if the kit used a generic title
    html = index.read_text(encoding="utf-8")
    title = page_data.get("title") or "Sales page"
    if "<title>" in html:
        html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1)
        index.write_text(html, encoding="utf-8")
    return index
