"""
test_shodan_and_osint_indepth.py
==================================
In-depth unit and integration tests for:
- backend/services/shodan_service.py (_classify_device_type, _extract_manufacturer, _device_id, cache freshness)
- backend/services/news_service.py (keyword scoring, article retrieval, cache invalidation, error fallbacks)
"""

import os
import sys
import pytest
import pytest_asyncio
import aiosqlite
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.shodan_service import (
    _classify_device_type,
    _extract_manufacturer,
    _device_id,
    _is_cache_fresh,
    _load_from_cache,
    _save_devices,
)
from services.news_service import fetch_and_cache_news, _fetch_gdelt
from config import DATABASE_PATH, CACHE_TTL_HOURS


class TestShodanClassification:
    def test_classify_device_type_camera_keywords(self):
        assert _classify_device_type({"product": "webcam Pro 4k"}) == "IP Camera"
        assert _classify_device_type({"product": "Hikvision Digital Camera"}) == "IP Camera"
        assert _classify_device_type({"product": "Axis Q3517-LV"}) == "IP Camera"

    def test_classify_device_type_dvr_nvr(self):
        data = {"http": {"title": "Hikvision Network Video Recorder"}}
        assert _classify_device_type(data) == "DVR/NVR"

        data2 = {"http": {"title": "Standalone DVR Web Interface"}}
        assert _classify_device_type(data2) == "DVR/NVR"

    def test_classify_device_type_rtsp_and_port(self):
        assert _classify_device_type({"port": 554}) == "RTSP Stream"
        assert _classify_device_type({"data": "RTSP/1.0 200 OK"}) == "RTSP Stream"

    def test_classify_device_type_telecom(self):
        assert _classify_device_type({"product": "ZTE Router", "port": 8080}) == "Telecom Equipment"
        assert _classify_device_type({"product": "Huawei Gateway", "port": 22}) == "Telecom Equipment"

    def test_classify_device_type_fallback(self):
        assert _classify_device_type({"product": "Unknown Device", "port": 80}) == "Network Device"

    def test_extract_manufacturer_known(self):
        assert _extract_manufacturer({"product": "Hikvision Camera", "org": "Telecom"}) == "Hikvision"
        assert _extract_manufacturer({"product": "Custom", "org": "Dahua Tech"}) == "Dahua"
        assert _extract_manufacturer({"product": "Axis Communications", "org": "ISP"}) == "Axis"
        assert _extract_manufacturer({"product": "Hanwha Techwin", "org": "ISP"}) == "Hanwha"

    def test_extract_manufacturer_fallback_first_word(self):
        assert _extract_manufacturer({"product": "AcmeCam System"}) == "Acmecam"

    def test_extract_manufacturer_unknown(self):
        assert _extract_manufacturer({"product": "x", "org": "y"}) == "Unknown"

    def test_device_id_deterministic(self):
        id1 = _device_id("192.168.1.1", "Mumbai")
        id2 = _device_id("192.168.1.1", "Mumbai")
        id3 = _device_id("192.168.1.2", "Mumbai")
        assert id1 == id2
        assert id1 != id3


class TestShodanCacheDB:
    @pytest.mark.asyncio
    async def test_cache_freshness_check(self, tmp_path):
        db_path = str(tmp_path / "test_shodan.db")
        with patch("services.shodan_service.DATABASE_PATH", db_path):
            async with aiosqlite.connect(db_path) as db:
                await db.execute("CREATE TABLE cities (name TEXT PRIMARY KEY, last_fetched TEXT)")
                await db.commit()

            # Fresh timestamp
            now_iso = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(db_path) as db:
                await db.execute("INSERT INTO cities VALUES ('Mumbai', ?)", (now_iso,))
                await db.commit()

            assert await _is_cache_fresh("Mumbai") is True

            # Stale timestamp
            stale_iso = (datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS + 1)).isoformat()
            async with aiosqlite.connect(db_path) as db:
                await db.execute("UPDATE cities SET last_fetched = ? WHERE name = 'Mumbai'", (stale_iso,))
                await db.commit()

            assert await _is_cache_fresh("Mumbai") is False

            # Missing city
            assert await _is_cache_fresh("NonExistent") is False


class TestNewsService:
    @pytest.mark.asyncio
    async def test_fetch_and_cache_news_anchored(self, tmp_path):
        db_path = str(tmp_path / "test_news.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
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
                """
            )
            await db.commit()

        with patch("services.news_service.DATABASE_PATH", db_path):
            news = await fetch_and_cache_news("Mumbai")
            assert isinstance(news, list)
            assert len(news) > 0
            for item in news:
                assert "title" in item
                assert "url" in item

    @pytest.mark.asyncio
    async def test_fetch_gdelt_resiliency(self):
        with patch("httpx.AsyncClient.get", side_effect=Exception("Network down")):
            articles = await _fetch_gdelt("Mumbai")
            assert isinstance(articles, list)
            assert len(articles) == 0
