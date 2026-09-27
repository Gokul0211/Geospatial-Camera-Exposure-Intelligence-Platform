"""
Build a copy of the COBRA-WATCH database that is safe to host publicly.

    python scripts/make_public_snapshot.py data/surveillancewatch.db data/public.db

What it does to the copy (the source DB is never modified):
  - device IDs: md5(ip:city) is reversible by brute force over IPv4, so every ID is
    replaced with an HMAC under a random key that is discarded when the script exits
    (IDs in camera_adjacency and alerts are rewritten to match)
  - ip set to 0.0.0.0; ports, owner_org, banner_snippet, raw_data cleared
  - lat/lon snapped to a grid (default 0.01 deg, about 1.1 km)
  - audit_ledger payloads are emptied, since they can embed camera IDs; the chain
    will no longer verify on the public copy, which is expected
"""

import argparse
import hashlib
import hmac
import secrets
import shutil
import sqlite3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--grid", type=float, default=0.01)
    args = ap.parse_args()

    shutil.copyfile(args.src, args.dst)
    key = secrets.token_bytes(32)
    new_id = lambda old: "cam_" + hmac.new(key, old.encode(), hashlib.sha256).hexdigest()[:16]
    snap = lambda v: None if v is None else round(round(v / args.grid) * args.grid, 4)

    db = sqlite3.connect(args.dst)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    cols = {t: {r[1] for r in db.execute(f"PRAGMA table_info({t})")} for t in tables}

    mapping = {old: new_id(old) for (old,) in db.execute("SELECT id FROM devices")}

    db.execute("PRAGMA foreign_keys=OFF")
    for old, new in mapping.items():
        db.execute("UPDATE devices SET id=? WHERE id=?", (new, old))
        if "camera_adjacency" in tables:
            db.execute("UPDATE camera_adjacency SET camera_id=? WHERE camera_id=?", (new, old))
            db.execute("UPDATE camera_adjacency SET nearby_camera_id=? WHERE nearby_camera_id=?", (new, old))
        if "alerts" in tables:
            db.execute("UPDATE alerts SET camera_id=? WHERE camera_id=?", (new, old))

    clear = [c for c in ("ports", "owner_org", "banner_snippet", "raw_data") if c in cols["devices"]]
    db.execute("UPDATE devices SET ip='0.0.0.0'" + "".join(f", {c}=NULL" for c in clear))

    for t in ("devices", "news_articles"):
        if t in tables:
            for rowid, lat, lon in db.execute(f"SELECT rowid, lat, lon FROM {t}").fetchall():
                db.execute(f"UPDATE {t} SET lat=?, lon=? WHERE rowid=?", (snap(lat), snap(lon), rowid))

    if "audit_ledger" in tables:
        db.execute("UPDATE audit_ledger SET payload='{}'")

    db.commit()
    db.execute("VACUUM")  # drop freed pages that still contain the old values
    db.close()
    print(f"Wrote {args.dst}: {len(mapping)} devices re-keyed and scrubbed.")


if __name__ == "__main__":
    main()
