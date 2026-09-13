"""
test_cold_start_service.py
============================
Tests for §5.2 — Cold-Start Trust Bootstrapping via Device-Fingerprint
Stereotyping. Verifies:
  1. A device with zero prior alerts is correctly identified as cold-start.
  2. With no comparable "digital twin" cluster, the prior falls back to 0.50.
  3. With a sufficiently large twin cluster (same manufacturer + port
     signature), the prior is bootstrapped from their historical scores
     instead of the flat neutral default.
  4. `compute_probabilistic_trust_score` actually shifts its posterior when
     given a non-default prior, and leaves existing callers (default 0.50)
     byte-for-byte unaffected.
"""

import sys
import os
import json
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import patch

from database import init_db
from services.trust_score_service import compute_probabilistic_trust_score


async def _init_test_db(db_path: str):
    with patch("database.DATABASE_PATH", db_path):
        await init_db()


async def _insert_device(db_path, device_id, manufacturer="Hikvision", ports=None, city="Mumbai"):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO devices (id, city, ip, manufacturer, ports)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, city, "10.0.0.1", manufacturer, json.dumps(ports or [80, 554])),
        )
        await db.commit()


async def _insert_alert(db_path, camera_id, trust_score, probabilistic_score=None):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO alerts
               (id, camera_id, city, event_type, trust_score, contributing_factors,
                corroborated_by, action_tier, probabilistic_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), camera_id, "Mumbai", "loitering", trust_score,
             "[]", "[]", "low_trust" if trust_score < 50 else "high_trust", probabilistic_score),
        )
        await db.commit()


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_cold_start.db")
    await _init_test_db(db_path)
    return db_path


class TestColdStartDetection:
    @pytest.mark.asyncio
    async def test_brand_new_device_is_cold_start(self, test_db):
        from services import cold_start_service
        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            assert await cold_start_service.is_cold_start_device("brand-new-cam") is True

    @pytest.mark.asyncio
    async def test_device_with_history_is_not_cold_start(self, test_db):
        from services import cold_start_service
        cam_id = "established-cam"
        await _insert_alert(test_db, cam_id, trust_score=80)
        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            assert await cold_start_service.is_cold_start_device(cam_id) is False


class TestStereotypePrior:
    @pytest.mark.asyncio
    async def test_no_twin_cluster_falls_back_to_flat_default(self, test_db):
        from services import cold_start_service
        device = {"id": "lonely-cam", "manufacturer": "Hikvision", "ports": "[554]"}
        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            result = await cold_start_service.compute_stereotype_prior(device)
        assert result["method"] == "flat_default"
        assert result["prior_probability"] == 0.50
        assert result["cluster_size"] == 0

    @pytest.mark.asyncio
    async def test_unknown_manufacturer_falls_back_to_flat_default(self, test_db):
        from services import cold_start_service
        device = {"id": "mystery-cam", "manufacturer": "Unknown", "ports": "[554]"}
        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            result = await cold_start_service.compute_stereotype_prior(device)
        assert result["method"] == "flat_default"

    @pytest.mark.asyncio
    async def test_twin_cluster_bootstraps_low_prior_for_bad_neighborhood(self, test_db):
        """
        Three other Hikvision devices sharing the same port signature, all
        with poor historical trust scores -> the new device's prior should be
        bootstrapped LOW, not flat 0.50.
        """
        from services import cold_start_service

        twin_ids = [f"twin-{i}" for i in range(3)]
        for tid in twin_ids:
            await _insert_device(test_db, tid, manufacturer="Hikvision", ports=[80, 554])
            await _insert_alert(test_db, tid, trust_score=15, probabilistic_score=10)

        new_device = {"id": "new-hikvision-cam", "manufacturer": "Hikvision", "ports": json.dumps([80, 554])}

        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            result = await cold_start_service.compute_stereotype_prior(new_device)

        assert result["method"] == "stereotype"
        assert result["cluster_size"] >= 3
        # Bad-neighborhood cluster (avg score ~10-15/100) should pull prior well below 0.50
        assert result["prior_probability"] < 0.50
        assert result["prior_probability"] >= cold_start_service.PRIOR_FLOOR

    @pytest.mark.asyncio
    async def test_twin_cluster_bootstraps_high_prior_for_good_neighborhood(self, test_db):
        from services import cold_start_service

        twin_ids = [f"good-twin-{i}" for i in range(4)]
        for tid in twin_ids:
            await _insert_device(test_db, tid, manufacturer="Axis", ports=[443, 554])
            await _insert_alert(test_db, tid, trust_score=95, probabilistic_score=92)

        new_device = {"id": "new-axis-cam", "manufacturer": "Axis", "ports": json.dumps([443, 554])}

        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            result = await cold_start_service.compute_stereotype_prior(new_device)

        assert result["method"] == "stereotype"
        assert result["prior_probability"] > 0.50
        assert result["prior_probability"] <= cold_start_service.PRIOR_CEILING

    @pytest.mark.asyncio
    async def test_dissimilar_port_signature_excluded_from_cluster(self, test_db):
        """A same-manufacturer device with a totally different port signature (Jaccard < 0.5) shouldn't count as a twin."""
        from services import cold_start_service

        await _insert_device(test_db, "different-ports-cam", manufacturer="Hikvision", ports=[8080, 9000, 9001])
        await _insert_alert(test_db, "different-ports-cam", trust_score=10)

        new_device = {"id": "new-cam", "manufacturer": "Hikvision", "ports": json.dumps([80, 554])}

        with patch.object(cold_start_service, "DATABASE_PATH", test_db):
            result = await cold_start_service.compute_stereotype_prior(new_device)

        assert result["method"] == "flat_default"


class TestProbabilisticScoreWithPrior:
    def test_default_prior_unchanged_from_flat_baseline(self):
        """Backward compatibility: omitting prior_probability behaves exactly as before."""
        device = {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-01-01"}
        result = compute_probabilistic_trust_score(device, corroborating_cameras=[])
        assert result["prior_probability"] == 0.50
        assert not any("cold_start_stereotype_prior" in f for f in result["factors"])

    def test_low_prior_pulls_posterior_down(self):
        """Same evidence, but a pessimistic cold-start prior should yield a lower posterior than the flat-0.50 baseline."""
        device = {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-01-01"}
        baseline = compute_probabilistic_trust_score(device, corroborating_cameras=[], prior_probability=0.50)
        pessimistic = compute_probabilistic_trust_score(device, corroborating_cameras=[], prior_probability=0.20)

        assert pessimistic["score"] < baseline["score"]
        assert pessimistic["prior_probability"] == 0.20
        assert any("cold_start_stereotype_prior" in f for f in pessimistic["factors"])

    def test_high_prior_pulls_posterior_up(self):
        device = {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": None}
        baseline = compute_probabilistic_trust_score(device, corroborating_cameras=[], prior_probability=0.50)
        optimistic = compute_probabilistic_trust_score(device, corroborating_cameras=[], prior_probability=0.80)

        assert optimistic["score"] > baseline["score"]
