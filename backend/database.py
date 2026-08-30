import aiosqlite
import asyncio
from config import DATABASE_PATH
import os


async def get_db():
    """Get a database connection. Caller must close it."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def _add_column_if_missing(db, table: str, column: str, coltype: str):
    """
    Idempotent ALTER TABLE helper. Safe to call on every app startup —
    no-ops if the column already exists, adds it if it doesn't.
    Required because init_db() runs every startup via the lifespan context
    manager in main.py, and plain ALTER TABLE throws on the second run.
    """
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        existing = {row[1] for row in await cursor.fetchall()}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


async def init_db():
    """Create all tables and indexes."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")

        # ── Core tables (unchanged from hackathon) ────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                ip TEXT NOT NULL,
                lat REAL,
                lon REAL,
                device_type TEXT,
                manufacturer TEXT,
                ports TEXT,
                owner_org TEXT,
                owner_type TEXT,
                ownership_confidence TEXT,
                first_seen TEXT,
                last_seen TEXT,
                banner_snippet TEXT,
                raw_data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                title TEXT,
                source TEXT,
                published_at TEXT,
                url TEXT UNIQUE,
                description TEXT,
                lat REAL,
                lon REAL,
                geo_confidence TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS risk_briefs (
                cluster_id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                brief_text TEXT,
                risk_level TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                name TEXT PRIMARY KEY,
                lat REAL,
                lon REAL,
                zoom_level INTEGER,
                last_fetched TIMESTAMP
            )
        """)

        # ── Phase 1: new columns on devices (idempotent — safe on re-run) ─────
        # firmware_version: raw version string from the Shodan banner/product field
        await _add_column_if_missing(db, "devices", "firmware_version", "TEXT")
        # auth_required: True/False/None — inferred by auth_detection.py from banner
        await _add_column_if_missing(db, "devices", "auth_required", "BOOLEAN")
        # known_cve_count: count of CVEs returned by NVD for this device's manufacturer
        await _add_column_if_missing(db, "devices", "known_cve_count", "INTEGER DEFAULT 0")
        # cve_ids: JSON array of CVE ID strings, e.g. ["CVE-2021-36260", ...]
        await _add_column_if_missing(db, "devices", "cve_ids", "TEXT")
        # last_patch_date: ISO date string — sourced from NVD 'published' date of most
        #   recent matched CVE (see vulnerability_service.py for population logic).
        #   NULL means unknown. Phase 2 treat NULL as "outdated" by default.
        await _add_column_if_missing(db, "devices", "last_patch_date", "TEXT")
        # vuln_last_checked: ISO timestamp of when CVE data was last refreshed
        await _add_column_if_missing(db, "devices", "vuln_last_checked", "TEXT")
        # Module C (BTP) — CVE category and CVSS severity (Oliver 2025, Famera 2025)
        # cve_categories: JSON list of category strings, e.g. ["auth_bypass", "rce"]
        await _add_column_if_missing(db, "devices", "cve_categories", "TEXT")
        # max_cvss: highest CVSS v3 base score (0.0–10.0) from NVD for this device
        await _add_column_if_missing(db, "devices", "max_cvss", "REAL")

        # ── Phase 1/2: new tables ─────────────────────────────────────────────
        # camera_adjacency: which cameras are physically close enough to corroborate
        # each other. Populated by a seed script (see scripts/seed_adjacency.py).
        await db.execute("""
            CREATE TABLE IF NOT EXISTS camera_adjacency (
                camera_id TEXT NOT NULL,
                nearby_camera_id TEXT NOT NULL,
                PRIMARY KEY (camera_id, nearby_camera_id)
            )
        """)

        # alerts: core of COBRA-WATCH — one row per detection event that was
        # processed through the trust-score pipeline. Replaces the fake WebSocket
        # random.choice() block once Phase 2 is wired in.
        # city is denormalized here (copied from devices.city at ingest time)
        # so GET /api/alerts?city= can filter without a join.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                camera_id TEXT NOT NULL,
                city TEXT,
                event_type TEXT NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trust_score INTEGER NOT NULL,
                contributing_factors TEXT NOT NULL,
                corroborated_by TEXT,
                action_tier TEXT NOT NULL,
                probabilistic_score INTEGER,
                decayed_score INTEGER,
                max_cvss REAL,
                feature_embedding TEXT
            )
        """)

        # ── Module E (BTP) — Tamper-Evident Audit Ledger (BIoT SLR 2026) ─────────
        # Persistent Merkle hash chain: survives server restarts for forensic use.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_hash TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # ── Indexes ────────────────────────────────────────────────────────────
        # Existing indexes (fast city/owner lookups)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_city ON devices(city)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_owner ON devices(city, owner_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_news_city ON news_articles(city)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_briefs_city ON risk_briefs(city)")
        # New indexes for alert queries (Phase 2)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_camera ON alerts(camera_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(detected_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_city ON alerts(city)")

        # Idempotent migration: add city to alerts for DBs created before Phase 2
        await _add_column_if_missing(db, "alerts", "city", "TEXT")
        # Idempotent migrations: BTP Module A/B/E/F columns
        await _add_column_if_missing(db, "alerts", "probabilistic_score", "INTEGER")
        await _add_column_if_missing(db, "alerts", "decayed_score", "INTEGER")
        await _add_column_if_missing(db, "alerts", "max_cvss", "REAL")
        await _add_column_if_missing(db, "alerts", "feature_embedding", "TEXT")
        # Ground-truth operator verdict & tiered notification metadata (Rasal 2025, Luna 2018)
        await _add_column_if_missing(db, "alerts", "operator_verdict", "TEXT")
        await _add_column_if_missing(db, "alerts", "verdict_recorded_at", "TEXT")
        await _add_column_if_missing(db, "alerts", "notification_channel", "TEXT")
        await _add_column_if_missing(db, "alerts", "notification_priority", "TEXT")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database initialized.")
