import asyncio
from ipwhois import IPWhois
from services.classifier import classify_owner_by_keywords, classify_owner_with_claude


def _whois_lookup(ip: str) -> dict:
    """Synchronous WHOIS lookup. Run in executor."""
    try:
        obj = IPWhois(ip)
        result = obj.lookup_rdap(depth=1)
        network = result.get("network") or {}
        org = network.get("name") or ""
        asn_desc = result.get("asn_description") or ""
        country = (network.get("country") or result.get("asn_country_code") or "")
        return {
            "owner_org": org or asn_desc or "Unknown",
            "asn_description": asn_desc,
            "country": country,
        }
    except Exception as e:
        # Common: rate-limited, private IP, or network issues
        return {"owner_org": "Unknown", "asn_description": "", "country": ""}


async def enrich_ownership(device: dict) -> dict:
    """Add owner_org, owner_type, ownership_confidence to a device dict."""
    loop = asyncio.get_event_loop()
    ip = device.get("ip", "")
    if not ip:
        device["owner_org"] = "Unknown"
        device["owner_type"] = "unknown"
        device["ownership_confidence"] = "low"
        return device

    whois_data = await loop.run_in_executor(None, _whois_lookup, ip)
    org = whois_data["owner_org"]
    asn_desc = whois_data["asn_description"]
    country = whois_data["country"]

    # Try keyword classification first (fast, free)
    owner_type, confidence = classify_owner_by_keywords(org, asn_desc)

    # If keyword matching is uncertain, try Claude classification
    # Only during prefetch (not live demo) — the cache will have the result
    if owner_type == "unknown" and confidence == "low" and org != "Unknown":
        try:
            claude_type = await classify_owner_with_claude(org, country)
            if claude_type != "unknown":
                owner_type = claude_type
                confidence = "medium"  # Claude-classified = medium confidence
        except Exception:
            pass  # Keep keyword result if Claude fails

    device["owner_org"] = org
    device["owner_type"] = owner_type
    device["ownership_confidence"] = confidence
    return device
