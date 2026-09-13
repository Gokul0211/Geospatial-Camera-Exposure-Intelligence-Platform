# Red-Team Findings: Corroboration Logic & Alert Pipeline

**Phase 4 — COBRA-WATCH Security Evaluation**

---

## Scope

This document red-teams the `+20 corroborated` bonus in the trust score formula and the `POST /api/detection-event` endpoint. The goal is to answer: can an adversary meaningfully inflate trust scores or inject high-trust alerts?

---

## Attack 1: Spoofed Corroboration via Fake `camera_adjacency` Rows

### Attack description
An adversary with write access to the `camera_adjacency` table inserts fake rows pairing a real (but vulnerable) camera with attacker-controlled "corroborating" camera IDs. They then spam `POST /api/detection-event` from those fake camera IDs, triggering the `+20 corroborated` bonus for their target camera.

### Test procedure
```python
# Attacker inserts fake adjacency
await db.execute("INSERT INTO camera_adjacency VALUES ('VICTIM_CAM', 'FAKE_001')")
await db.execute("INSERT INTO camera_adjacency VALUES ('VICTIM_CAM', 'FAKE_002')")

# Attacker spams detection events from fake cameras
await client.post("/api/detection-event", json={"camera_id": "FAKE_001", "event_type": "loitering", ...})
await client.post("/api/detection-event", json={"camera_id": "FAKE_002", "event_type": "loitering", ...})

# Now victim camera gets +20 corroboration bonus
await client.post("/api/detection-event", json={"camera_id": "VICTIM_CAM", ...})
```

### Result
**Partial success with important limitations:**

1. The `+20 corroboration` bonus CAN be obtained this way — this is the real vulnerability.
2. **However**, for a device with strong negative signals (auth=False, known CVEs, unknown owner, outdated firmware), the maximum score after corroboration bonus is `100 - 30 - 25 - 20 - 15 + 20 = 30`. Still `low_trust`. The corroboration bonus cannot rescue a genuinely bad device.
3. For a *borderline* device (e.g., score=60 without corroboration), the bonus could push it to `high_trust`. This is the actual risk surface.

### Fixes applied
- `POST /api/detection-event` now requires `X-API-Key` header → **attacker needs the API key to post events at all**. This is the primary mitigation. Without the key, the attack is impossible in production.
- **Documented limitation (v1):** No rate limiting on `POST /api/detection-event`. If the API key leaks, an attacker with the key can spam events. Rate limiting should be added in v2 (e.g., slowapi).

### Residual risk (documented for report)
If the API key leaks AND an attacker can both write to `camera_adjacency` (requires DB access) AND post events: corroboration inflation is possible for borderline-score devices. Mitigations in v2:
- Store `camera_adjacency` as read-only config (not writable via any API endpoint)
- Rate limit `POST /api/detection-event` per `camera_id` (e.g., max 1 event/minute per camera)
- Track "corroboration velocity" — if the same two camera IDs corroborate each other repeatedly, flag it

---

## Attack 2: Replay of a Genuine High-Trust Alert

### Attack description
An attacker captures a valid `POST /api/detection-event` request body from a legitimate high-trust camera and replays it repeatedly to flood the alerts feed.

### Result
**Succeeds (v1 documented limitation):**
- Each replay creates a new `alerts` row with a unique `alert_id` (UUID)
- The trust score is identical (same camera, same device signals, same corroboration state)
- The alert appears legitimate in `GET /api/alerts`
- A flood of replayed alerts from a genuine camera would obscure real events

### Fix applied
**None in v1** — documented limitation. The primary defense (API key auth) prevents unauthenticated replays. Replay from an attacker who possesses the key is a harder problem.

### Mitigations for v2
- **Nonce/timestamp validation**: reject requests where `detected_at` is > 60s old
- **Idempotency key**: accept a client-generated `idempotency_key` in the request body; reject duplicates within a time window
- **Per-camera rate limiting**: max N alerts/minute per camera_id

---

## Attack 3: Metadata Payload Injection

### Attack description
Attacker tries to manipulate trust score by including fake device fields in the `POST /api/detection-event` payload:
```json
{
  "camera_id": "VICTIM_CAM",
  "event_type": "loitering",
  "confidence": 0.99,
  "metadata": {"known_cve_count": 0, "auth_required": true, "owner_type": "government"}
}
```

### Result
**Fails completely.** The backend handler (`alerts.py`) loads the device row directly from the database using `camera_id` only. The `metadata` field is stored as-is in `alerts.metadata` but **never** fed into `compute_trust_score()`. The trust score uses only the DB-persisted device fields.

### Fix
**By construction** — no change needed. This is a deliberate architectural decision: device properties are trusted only from the DB (populated by Shodan + Phase 1 services), not from the caller.

---

## Attack 4: No API Key (Unauthenticated Alert Injection)

### Attack description
Before Phase 4, `POST /api/detection-event` required no authentication. Any attacker could inject alerts.

### Result (pre-Phase 4)
An attacker could POST a detection event for any camera ID with any event_type. If the camera happened to have good device signals (auth=True, no CVEs, known owner, recent patch), they could inject a `high_trust` alert directly.

### Fix applied
**Phase 4 implementation:** `X-API-Key` header required. Key compared with `hmac.compare_digest()` (constant-time, prevents timing attacks). Auth disabled when `DETECTION_API_KEY` is empty (local dev default).

---

## Summary Table

| Attack | Succeeds in v1? | Primary mitigation | Residual risk |
|---|---|---|---|
| Spoofed corroboration (with API key + DB access) | Partial (borderline devices only) | API key auth | Key leak + DB write access combo |
| Replay attack (with API key) | Yes | API key auth | Key holder can replay |
| Metadata payload injection | No | Architecture | None |
| Unauthenticated alert injection | No (fixed) | X-API-Key auth | None in prod |

---

## Rate Limiting (Not Yet Implemented — v2 Item)

There is currently no rate limiting on `POST /api/detection-event`. An authenticated caller with the key can:
- Spam events faster than the 15-minute corroboration window, potentially pre-seeding false corroboration
- Flood the alerts feed with replayed events

**Recommended v2 fix:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/detection-event")
@limiter.limit("10/minute")
async def receive_detection_event(...):
    ...
```

---

## Verdict

The trust score formula is robust against naive attacks (metadata injection fails by construction; unauthenticated injection is blocked by API key auth). The real residual risks are:
1. Corroboration inflation by an attacker with both the API key and DB write access
2. Replay flooding by an API-key holder

Both are documented v2 items, not silent oversights. The viva answer is: "we've identified and documented these attack surfaces; the API key closes the unauthenticated surface; the remaining risks require rate limiting and replay protection which are planned for v2."
