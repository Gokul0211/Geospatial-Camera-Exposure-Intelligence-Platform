"""
nl_query_router.py
====================
Module H — Natural-language map query.

Parses a free-text query ("unauthenticated government cameras in Delhi with
known CVEs") into the structured filter shape the frontend already applies to
its in-memory device list. Uses the same Groq client/key already wired in for
risk-brief generation (services/claude_service.py) — no new API dependency.

Deliberately narrow scope: this endpoint does NOT touch the database or the
trust-scoring pipeline. It only maps text -> filter parameters; the frontend
applies them exactly like a manually-clicked filter chip + search box, so a
malformed or low-confidence LLM response can never do anything worse than
"filter didn't match what you meant" — it cannot corrupt data or bypass any
security control.
"""

from __future__ import annotations

import json
import re

from fastapi import APIRouter
from pydantic import BaseModel

from config import GROQ_API_KEY, GROQ_MODEL

router = APIRouter()

VALID_CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "All India"]
VALID_OWNER_TYPES = ["government", "telecom", "corporate"]

_SYSTEM_PROMPT = (
    "You translate a security analyst's natural-language request about a camera-exposure "
    "map into a strict JSON filter object. Respond with ONLY the JSON object, no prose, "
    "no markdown fences.\n\n"
    "Schema:\n"
    "{\n"
    '  "auth_required": null | false,   // false means "unauthenticated / open / no auth"; null = not mentioned\n'
    '  "has_cve": null | true,          // true means "has known CVEs / vulnerable"; null = not mentioned\n'
    '  "owner_type": null | "government" | "telecom" | "corporate",\n'
    '  "city": null | one of ' + json.dumps(VALID_CITIES) + ",\n"
    '  "search_text": "",               // any leftover keyword (manufacturer, IP fragment, org name) not covered above\n'
    '  "explanation": ""                // one short sentence restating what you understood\n'
    "}\n\n"
    "Only set a field when the request actually mentions it. Never invent a city or owner "
    "type that wasn't said or clearly implied."
)

_FEWSHOT = [
    {"role": "user", "content": "unauthenticated government cameras in Delhi with known CVEs"},
    {"role": "assistant", "content": json.dumps({
        "auth_required": False, "has_cve": True, "owner_type": "government", "city": "Delhi",
        "search_text": "", "explanation": "Unauthenticated, vulnerable, government-owned cameras in Delhi.",
    })},
    {"role": "user", "content": "show me hikvision cameras"},
    {"role": "assistant", "content": json.dumps({
        "auth_required": None, "has_cve": None, "owner_type": None, "city": None,
        "search_text": "hikvision", "explanation": "Devices matching manufacturer Hikvision.",
    })},
]


class NLQueryRequest(BaseModel):
    query: str
    current_city: str | None = None


def _sanitize(parsed: dict) -> dict:
    city = parsed.get("city")
    if city not in VALID_CITIES:
        city = None
    owner_type = parsed.get("owner_type")
    if owner_type not in VALID_OWNER_TYPES:
        owner_type = None
    return {
        "auth_required": False if parsed.get("auth_required") is False else None,
        "has_cve": True if parsed.get("has_cve") is True else None,
        "owner_type": owner_type,
        "city": city,
        "search_text": str(parsed.get("search_text") or "")[:100],
        "explanation": str(parsed.get("explanation") or "")[:200],
    }


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Models occasionally wrap JSON in ```json fences despite instructions — strip them.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


@router.post("/nl-query")
async def parse_natural_language_query(req: NLQueryRequest):
    """
    Returns the sanitized structured filter, or a null-filter fallback with
    `search_text` set to the raw query if Groq is unavailable/unparseable —
    the frontend then just falls back to a plain text search, never a hard error.
    """
    fallback = {
        "auth_required": None, "has_cve": None, "owner_type": None, "city": None,
        "search_text": req.query.strip()[:100],
        "explanation": "Could not parse — falling back to plain text search.",
        "parsed_by_ai": False,
    }

    if not GROQ_API_KEY or not req.query.strip():
        return fallback

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}, *_FEWSHOT, {"role": "user", "content": req.query}]
        res = await client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=300,
            temperature=0.1,
            messages=messages,
        )
        content = res.choices[0].message.content or ""
        parsed = _extract_json(content)
        sanitized = _sanitize(parsed)
        sanitized["parsed_by_ai"] = True
        return sanitized
    except Exception as e:
        fallback["explanation"] = f"AI parse failed ({type(e).__name__}) — falling back to plain text search."
        return fallback
