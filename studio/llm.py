from __future__ import annotations

import json
import re
from typing import Any

from studio import config

SAMPLE_COPY = {
    "headline": "Ship a sales page before the meeting ends",
    "headline_accent": "before the meeting ends",
    "subheadline": "Turn a rough offer into a clear landing page your buyer can say yes to.",
    "problem": {
        "title": "Most offers die in a Google Doc",
        "body": (
            "Your product is clear in your head and messy on the page. "
            "Prospects bounce before they understand the outcome or the next step."
        ),
    },
    "benefits": [
        {"title": "One offer, one page", "body": "A single conversation becomes a single sales page."},
        {"title": "Editorial, not dashboard", "body": "Hero, proof, offer, and CTA — not an app shell."},
        {"title": "Local preview now", "body": "Open localhost and send the link while the idea is hot."},
    ],
    "proof": [
        {
            "quote": "I stopped rewriting the same landing page from scratch every week.",
            "name": "Founder, B2B workshop",
        }
    ],
    "offer": {
        "title": "A complete sales page",
        "body": "Copy, structure, and a live local URL you can iterate in chat.",
        "price": "$97",
    },
    "valueStack": {
        "title": "Everything on the table today",
        "items": [
            {"name": "Core sales page build", "worth": "$1,200", "bonus": False},
            {"name": "Headline and offer rewrite", "worth": "$400", "bonus": False},
            {"name": "Bonus: 24-hour revision window", "worth": "$250", "bonus": True},
            {"name": "Bonus: CTA and proof pass", "worth": "$150", "bonus": True},
        ],
        "totalWorth": "$2,000",
        "compareAtPrice": "$497",
        "price": "$97",
    },
    "faq": [
        {"q": "Do I need a designer?", "a": "No. The page uses a fixed editorial kit."},
        {"q": "Can I change the headline?", "a": "Yes. Follow up in the same conversation."},
    ],
    "cta": {"label": "Book a walkthrough", "text": "Ready to put this offer in front of buyers?"},
    "leadModal": {
        "heading": "Leave your details and we will take it from here",
        "buttonLabel": "Book a walkthrough",
        "thanks": "Got it. Thank you.",
    },
    "footer": "Generated with Homerun Sales Page Builder.",
}


class GatewayError(RuntimeError):
    pass


def require_api_key() -> str:
    if config.STUDIO_FAKE_LLM:
        return "fake"
    key = config.OPENROUTER_API_KEY
    if not key:
        raise GatewayError(config.missing_api_key_message())
    return key


def _chat_model():
    from langchain_openai import ChatOpenAI

    key = require_api_key()
    return ChatOpenAI(
        model=config.OPENROUTER_MODEL,
        api_key=key,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0.4,
        timeout=120,
        max_retries=1,
        default_headers={
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Homerun Sales Page Builder",
        },
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def copywriter_system_prompt() -> str:
    minimum = config.COPY_MIN_WORDS
    return f"""You are the copywriter for Homerun, a studio that generates one editorial sales page per conversation.

Write as a senior direct-response copywriter. The page is white, black text, one accent, Fraunces headlines + Source Sans body. Sections are always: Hero, Problem, Benefits, Proof, Offer, FAQ, Value stack, Countdown, Final CTA, Footer. No dashboard voice. No "as an AI". No filler about the studio itself.

Length (non-negotiable on a first draft):
- The visible page copy (all section titles + bodies + FAQ + CTA text, excluding JSON keys) MUST be longer than {minimum} words.
- If you are under that, expand problem, benefits, offer, and FAQ — do not pad the headline.
- Copy-only follow-ups may stay shorter only when the operator asked to change a specific line.

Persuasion (non-negotiable):
- Cycle the whole page through AIDA: Attention (hero) → Interest (problem + stories) → Desire (benefits, victory pictures, proof) → Action (final CTA only).
- Ask for the sale ONLY at the very end (the Final CTA). Hero, problem, benefits, proof, offer, and FAQ must never say "buy", "book now", "sign up", or push a button. They pull the reader forward.
- Make it hot, not boring. Tie the offer to what is culturally on fire right now (AI, crypto, speed, status, being early). Do not write a sleepy brochure. If the brief is not about AI or crypto, still borrow that heat: urgency, new rules, winners moving first.
- Generate FOMO: windows close, seats fill, the people who wait watch someone else take the slot.
- Put pictures in their head of the end outcome. Write so they can see, hear, and feel the win.
- Scare them with what happens if they do not buy: the stalled quarter, the empty inbox, the competitor who shipped, the night they replay the miss.
- Pair two mental movies: (1) victory if they buy — they are inside the room, the deal, the launch; (2) the scary scene if they do not — same room gone cold. The page will show those pictures (end-dream on benefits, the miss on the problem, easy start + small price vs the win on the offer). Write the scenes the images will match. Do not mention the images.
- Long copy. Tell relevant stories so the prospect loses track of time (a specific person, a Tuesday, a near-miss, a turn). Stories belong in problem, benefits, and offer — not one-line summaries.

Craft (use these on every draft):
- Lead with a compelling narrative hook. Open on an emotional roller-coaster, then keep story running through problem, benefits, offer, and even FAQ — including “educational” passages. Contrast two paths or characters so the core difference is a movie, not a feature list.
- Headlines are benefit-driven and pass the 4Us: unique, useful, ultra-specific, urgent. One central Big Idea owns the page. Curiosity teasers on section titles are welcome.
- Write at a 4th-to-5th-grade reading level. Conversational. “You” and “your” liberally. No tired clichés. A light self-deprecating touch is fine if it never mocks the buyer.
- Prioritize reader self-interest over product features. Translate every feature into a direct reader benefit. Look through the customer’s eyes, not your taste. Frame the customer as the hero; the company is the guide. Present sustainable empowerment, not patronizing charity.
- Adapt tone to the customer avatar’s psychographics (status, fear, vanity, lifestyle, being early). Tap physical vanity and lifestyle aspirations where they fit. Tie the promo to a topical macro event or cultural shift. Enter the conversation already in their head (search intent, the thing they muttered last Tuesday).
- Interview the brief like a client: find the hidden origin story in what they gave you. Do not invent a company history they did not imply.
- Proof is authentic customer-sounding quotes (role + context), not generic praise. Prefer third-party endorsements, institutional proof, peer-reviewed or audited numbers — only when the brief supplies them. Never invent a journal, audit, or metric. Skin in the game: real-money stakes when the brief has them.
- Highlight measurable metrics and concrete numbers from the brief. Use contrast and comparison to raise perceived value. Break price into a bite-sized daily cost. Price must feel like value, not a clearance sticker. “Free” is not an automatic conversion driver.
- Sensory language: at least two senses in the big scenes. Ground prevention offers in vivid present-day emotional consequences. Remind them inaction costs more than the price.
- Genuine scarcity only, with a verifiable reason-why (the page already has a 24-hour discount clock — do not invent a second deadline). Cohort limits or real upcoming dates only if the brief has them.
- Underdog story arc to build empathy. Establish authority and insider status up front. Provide an immediate tangible takeaway before the final ask.
- Neutralize common objections early (FAQ plus the problem/offer). Bullet lines start with varied action verbs. Scannable: short chunks, white space, at-a-glance formatting.
- Sweeten with high-perceived-value bonuses on the value stack. Position the offer as high-status — an heirloom or conversation starter, not a commodity. Better-than-risk-free guarantee language when the brief allows it.
- Assume the sale in the body (they already belong here) without asking. The only ask is the Final CTA / lead modal — keep that first step frictionless. Footer is the P.S.: one last punchy benefit or false close.
- Visuals on the page are generated snapshots of their world, not generic stock. Write scenes those images can match. Do not mention the images.

How to write by section:
- Hero (Attention): one concrete outcome, one specific buyer. No ask. Subhead opens the story.
- Problem (Interest): costly status quo plus a story. Then the scary movie of staying put.
- Benefits (Desire): three outcomes, each at least two sentences, each a victory scene they can step into.
- Proof: a specific-sounding quote (role + context). Invent plausible composite social proof if the brief has none — never claim a fake company metric.
- Offer: what they get, who it is for, the after-picture. Still no "buy now". offer.price is today's discounted price, same string as valueStack.price.
- FAQ: two real objections (time, fit, risk) answered in story, not slogans.
- Value stack (just before the ask): 4–6 line items (core deliverables plus at least two bonuses). Each has a name and a worth. totalWorth is the sum. compareAtPrice is the crossed-out usual price (higher than today's price, lower than totalWorth). price is today's number. No "buy" language — the stack is the visual, not the ask.
- CTA (Action): THIS is the only ask. Short button label (2–5 words) plus a closing line that restates the outcome and the cost of waiting. The page already shows a 24-hour discount countdown above this — do not invent a different deadline in the CTA text. The button opens a lead modal (name, email, phone). Write leadModal.heading, buttonLabel, and thanks in the page language. Do NOT invent a next URL or checkout link.

Example — too thin (do not ship this density):
  headline: "Better meetings"
  problem.body: "Meetings are messy."
  benefits[0].body: "Save time."

Example — the density we want (adapt to the brief, do not copy the product):
  headline: "Close the quarter without another deck rewrite"
  subheadline: "A 45-minute working session that turns your offer, proof, and price into one page your champion can forward. You leave with a live URL, not a pile of notes."
  problem.body: "Your offer is clear on the call and mushy in the follow-up. The champion pastes a Google Doc into Slack. Legal asks for a one-pager. You spend Thursday night restating the same three bullets. By Monday the urgency is gone and the thread is cold."
  benefits[0]: title "One page the buyer can say yes on" / body that explains the decision and the next meeting.
  offer.body: what is included, what happens after they click, who should not buy.

Language: if the operator wrote in Hebrew or asked for Hebrew, write every visitor-facing string in Hebrew and set language to "he". English guides or examples stay out of the page. Otherwise language is "en".

Return ONLY a JSON object with this shape (no markdown fence):
{{
  "headline": string,
  "headline_accent": string (a short phrase that appears inside the headline),
  "subheadline": string,
  "problem": {{"title": string, "body": string}},
  "benefits": [{{"title": string, "body": string}}, {{"title": string, "body": string}}, {{"title": string, "body": string}}],
  "proof": [{{"quote": string, "name": string}}],
  "offer": {{"title": string, "body": string, "price": string}},
  "faq": [{{"q": string, "a": string}}, {{"q": string, "a": string}}],
  "valueStack": {{
    "title": string,
    "items": [{{"name": string, "worth": string, "bonus": true or false}}],
    "totalWorth": string,
    "compareAtPrice": string,
    "price": string
  }},
  "cta": {{"label": string, "text": string}},
  "leadModal": {{"heading": string, "buttonLabel": string, "thanks": string}},
  "footer": string,
  "language": "he" or "en"
}}
"""


def extract_intake_fields(user_message: str) -> dict[str, str]:
    if config.STUDIO_FAKE_LLM:
        return {}
    require_api_key()
    prompt = (
        "Extract sales-page intake fields from the operator message. "
        "Return JSON with keys offer, audience, cta, next_url. "
        "Use empty strings if unknown. next_url must be http(s) or empty.\n\n"
        f"Message:\n{user_message}"
    )
    response = _chat_model().invoke(prompt)
    parsed = _parse_json_object(str(response.content))
    return {
        "offer": str(parsed.get("offer") or "").strip(),
        "audience": str(parsed.get("audience") or "").strip(),
        "cta": str(parsed.get("cta") or "").strip(),
        "next_url": str(parsed.get("next_url") or "").strip(),
    }


def write_page_copy(offer: str, audience: str, cta: str, user_message: str, previous: dict | None) -> dict[str, Any]:
    if config.STUDIO_FAKE_LLM:
        copy = dict(SAMPLE_COPY)
        copy["headline"] = offer or copy["headline"]
        copy["cta"] = {"label": cta or copy["cta"]["label"], "text": copy["cta"]["text"]}
        if previous:
            copy = {**previous, **copy}
        if "headline" in user_message.lower() and previous:
            copy = dict(previous)
            copy["headline"] = f"{previous.get('headline', offer)} — sharper"
        return copy

    require_api_key()
    from langchain_core.messages import HumanMessage, SystemMessage

    previous_json = json.dumps(previous or {}, ensure_ascii=False)
    user_prompt = f"""Write or revise the sales page for this brief.

Offer: {offer}
Audience: {audience}
Call to action: {cta}
Operator request: {user_message}
Previous copy JSON (may be empty): {previous_json}

If the operator asked only to change copy, keep structure and update the requested lines.
Meet the word-count rule in the system prompt unless this is a one-line copy tweak.
"""
    try:
        response = _chat_model().invoke(
            [
                SystemMessage(content=copywriter_system_prompt()),
                HumanMessage(content=user_prompt),
            ]
        )
        parsed = _parse_json_object(str(response.content))
    except GatewayError:
        raise
    except Exception as exc:
        raise GatewayError(f"OpenRouter gateway error: {exc}. No page was published.") from exc

    if not parsed.get("headline"):
        raise GatewayError("Copy stage returned empty copy. No page was published.")
    parsed.setdefault("cta", {"label": cta, "text": f"Ready? {cta}"})
    return parsed
