"""
Owner type classification logic.
Primary: keyword matching (fast, free).
Fallback: Claude single-word classification (for ambiguous orgs).
"""
from config import OWNER_TYPE_KEYWORDS


def classify_owner_by_keywords(org: str, asn_description: str) -> tuple[str, str]:
    """
    Classify owner type using keyword matching.
    Returns (owner_type, confidence).
    """
    text = f"{org} {asn_description}".lower()

    for owner_type, keywords in OWNER_TYPE_KEYWORDS.items():
        matches = sum(1 for k in keywords if k in text)
        if matches >= 2:
            return owner_type, "high"
        if matches == 1:
            return owner_type, "medium"

    return "unknown", "low"


async def classify_owner_with_claude(org: str, country: str) -> str:
    """
    Use Groq (llama-3.3-70b) to classify ambiguous orgs that keyword matching couldn't resolve.
    Returns one of: government, corporate, telecom, unknown.
    Only called when keyword matching returns 'unknown' with 'low' confidence.
    """
    from config import GROQ_API_KEY, GROQ_MODEL
    from groq import AsyncGroq

    if not GROQ_API_KEY:
        return "unknown"

    client = AsyncGroq(api_key=GROQ_API_KEY)
    prompt = (
        f"Classify this organization as one of: government, corporate, telecom, unknown.\n"
        f"Organization name: \"{org}\"\n"
        f"Country: \"{country}\"\n"
        f"Respond with only one word: government, corporate, telecom, or unknown."
    )

    try:
        res = await client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        result = (res.choices[0].message.content or "").strip().lower()
        if result in ("government", "corporate", "telecom"):
            return result
        return "unknown"
    except Exception:
        return "unknown"
