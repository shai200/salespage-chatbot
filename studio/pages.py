from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from studio import config

SECTION_IMPORTS = (
    "Hero",
    "Problem",
    "Benefits",
    "Proof",
    "Offer",
    "FAQ",
    "FinalCTA",
    "Footer",
)

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


def _write_app_jsx(site_dir: Path, data: dict[str, Any]) -> None:
    hero = data.get("hero", {})
    problem = data.get("problem", {})
    benefits = data.get("benefits", [])
    proof = data.get("proof", [])
    offer = data.get("offer", {})
    faq = data.get("faq", [])
    cta = data.get("cta", {})
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
  }},
  benefits: [
    {benefit_items}
  ],
  proof: [
    {proof_items}
  ],
  offer: {{
    title: {_jsx_string(offer.get("title"))},
    body: {_jsx_string(offer.get("body"))},
    price: {_jsx_string(offer.get("price"))},
    ctaLabel: {_jsx_string(offer.get("ctaLabel"))},
  }},
  faq: [
    {faq_items}
  ],
  cta: {{
    text: {_jsx_string(cta.get("text"))},
    label: {_jsx_string(cta.get("label"))},
  }},
  footer: {_jsx_string(footer)},
}};

export default function App() {{
  return (
    <main className="page">
      <Hero {{...page.hero}} />
      <Problem {{...page.problem}} />
      <Benefits items={{page.benefits}} />
      <Proof items={{page.proof}} />
      <Offer {{...page.offer}} />
      <FAQ items={{page.faq}} />
      <FinalCTA {{...page.cta}} />
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
        "problem": copy.get("problem") or {"title": "", "body": ""},
        "benefits": copy.get("benefits") or [],
        "proof": copy.get("proof") or [],
        "offer": {
            **(copy.get("offer") or {}),
            "ctaLabel": cta_label,
        },
        "faq": copy.get("faq") or [],
        "cta": copy.get("cta") or {"label": cta_label, "text": ""},
        "footer": copy.get("footer") or "Generated with Homerun Sales Page Builder.",
        "images_pending": bool(visuals.get("images_pending", True)),
    }


def write_site(site_dir: Path, page_data: dict[str, Any]) -> None:
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
