from groq import AsyncGroq
import aiosqlite
import json
from datetime import datetime, timezone
from config import GROQ_API_KEY, DATABASE_PATH, GROQ_MODEL


SYSTEM_PROMPT = (
    "You are a neutral, factual surveillance infrastructure analyst. "
    "You analyze OSINT data about surveillance technology deployments and produce concise, accurate risk assessments. "
    "You never editorialize, you never take political sides, and you always distinguish between confirmed facts and inferred assessments. "
    "Your writing style is Reuters wire service — precise, factual, dense."
)


def _build_prompt(req):
    owner_str = ", ".join(f"{k}: {v}" for k, v in req["owner_types"].items() if v > 0)
    news_str = "\n".join(f"- {h}" for h in req.get("nearby_news_headlines", [])) or "No recent news found."
    return (
        f"Given the following surveillance infrastructure data, write a factual 3-paragraph risk brief.\n\n"
        f"Location: {req['area_description']}, {req['city']}\n"
        f"Devices detected: {req['device_count']}\n"
        f"Device types: {', '.join(req['device_types'])}\n"
        f"Manufacturers: {', '.join(req['manufacturers'])}\n"
        f"Ownership breakdown: {owner_str}\n"
        f"Recent news context:\n{news_str}\n\n"
        f"Write exactly 3 paragraphs:\n"
        f"1. Technical summary — what infrastructure exists and its capabilities\n"
        f"2. Ownership and operational context — who controls it and any known usage context from the news\n"
        f"3. Risk assessment — proportionality, legal grounding, and any concerning patterns\n\n"
        f"Rules: No bullet points. No headers. No editorializing. No activist language. "
        f"Write like a Reuters journalist, not an activist. Be factual and neutral."
    )


def _risk_level(text):
    t = text.lower()
    scores = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for w in ["critical", "severely", "alarming", "grave", "urgent", "pervasive", "unchecked"]:
        if w in t:
            scores["CRITICAL"] += 3
    for w in ["high risk", "significant concern", "substantial", "disproportionate",
              "excessive", "no oversight", "legal vacuum", "unauthorized"]:
        if w in t:
            scores["HIGH"] += 2
    for w in ["moderate", "warrants attention", "notable", "raises questions",
              "unclear", "inconsistent", "limited oversight", "opaque"]:
        if w in t:
            scores["MEDIUM"] += 1
    for w in ["proportionate", "adequate", "standard", "routine", "established framework"]:
        if w in t:
            scores["LOW"] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "MEDIUM"


async def _get_cached(cluster_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM risk_briefs WHERE cluster_id = ?", (cluster_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def _save(cluster_id, city, brief_text, risk_level):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO risk_briefs (cluster_id, city, brief_text, risk_level, generated_at) VALUES (?, ?, ?, ?, ?)",
            (cluster_id, city, brief_text, risk_level, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()


async def generate_brief(req):
    cluster_id = req["cluster_id"]

    cached = await _get_cached(cluster_id)
    if cached:
        return {"cluster_id": cluster_id, "brief_text": cached["brief_text"], "risk_level": cached["risk_level"], "from_cache": True}

    if not GROQ_API_KEY:
        return {"cluster_id": cluster_id, "brief_text": "Analysis unavailable — API key not configured.", "risk_level": "MEDIUM", "from_cache": False}

    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        res = await client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(req)},
            ],
        )
        brief_text = res.choices[0].message.content or ""
    except Exception as e:
        print(f"[groq error] {e}")
        return {"cluster_id": cluster_id, "brief_text": "Analysis temporarily unavailable.", "risk_level": "MEDIUM", "from_cache": False}

    level = _risk_level(brief_text)
    await _save(cluster_id, req["city"], brief_text, level)
    return {"cluster_id": cluster_id, "brief_text": brief_text, "risk_level": level, "from_cache": False}


async def generate_brief_stream(req):
    cluster_id = req["cluster_id"]

    cached = await _get_cached(cluster_id)
    if cached:
        yield f"data: {json.dumps({'type': 'text', 'content': cached['brief_text']})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'risk_level': cached['risk_level']})}\n\n"
        return

    if not GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'text', 'content': 'Analysis unavailable — API key not configured.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'risk_level': 'MEDIUM'})}\n\n"
        return

    client = AsyncGroq(api_key=GROQ_API_KEY)
    full_text = ""

    try:
        stream = await client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1000,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(req)},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_text += delta
                yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"

        level = _risk_level(full_text)
        await _save(cluster_id, req["city"], full_text, level)
        yield f"data: {json.dumps({'type': 'done', 'risk_level': level})}\n\n"
    except Exception as e:
        print(f"[groq error] {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:100]})}\n\n"
