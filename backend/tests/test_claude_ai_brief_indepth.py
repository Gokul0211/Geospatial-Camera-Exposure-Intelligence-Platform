"""
test_claude_ai_brief_indepth.py
================================
In-depth unit & integration testing for backend/services/claude_service.py:
- Prompt template formatting & parameter validation
- Keyword-based risk level classification (_risk_level)
- Database caching & cache hit behavior
- API error fallback handling when API key is missing or raises network/rate errors
- Response structure integrity
"""

import os
import sys
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.claude_service import _build_prompt, _risk_level, generate_brief
from config import DATABASE_PATH


class TestClaudeBriefService:
    def test_build_prompt_formatting(self):
        req = {
            "cluster_id": "c123",
            "city": "Mumbai",
            "area_description": "Marine Drive",
            "device_count": 15,
            "device_types": ["IP Camera", "DVR/NVR"],
            "manufacturers": ["Hikvision", "Dahua"],
            "owner_types": {"government": 10, "commercial": 5, "unknown": 0},
            "nearby_news_headlines": ["Protest scheduled near coastline", "High surveillance traffic"],
        }
        prompt = _build_prompt(req)
        assert "Marine Drive, Mumbai" in prompt
        assert "Devices detected: 15" in prompt
        assert "IP Camera, DVR/NVR" in prompt
        assert "Hikvision, Dahua" in prompt
        assert "government: 10" in prompt
        assert "Protest scheduled near coastline" in prompt
        assert "Write exactly 3 paragraphs" in prompt

    def test_build_prompt_empty_news(self):
        req = {
            "cluster_id": "c456",
            "city": "Delhi",
            "area_description": "Connaught Place",
            "device_count": 2,
            "device_types": ["IP Camera"],
            "manufacturers": ["Axis"],
            "owner_types": {"unknown": 2},
            "nearby_news_headlines": [],
        }
        prompt = _build_prompt(req)
        assert "No recent news found." in prompt

    def test_risk_level_heuristics(self):
        assert _risk_level("The situation is critical and severely alarming.") == "CRITICAL"
        assert _risk_level("There is high risk and significant concern regarding privacy.") == "HIGH"
        assert _risk_level("The camera density is moderate and raises questions.") == "MEDIUM"
        assert _risk_level("The surveillance deployment is proportionate and follows an established framework.") == "LOW"
        assert _risk_level("Generic text without trigger words.") == "MEDIUM"

    @pytest.mark.asyncio
    async def test_generate_brief_missing_api_key(self, tmp_path):
        db_path = str(tmp_path / "test_brief.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_briefs (
                    cluster_id TEXT PRIMARY KEY,
                    city TEXT,
                    brief_text TEXT,
                    risk_level TEXT,
                    generated_at TEXT
                )
                """
            )
            await db.commit()

        req = {
            "cluster_id": "cluster_test_no_key",
            "city": "Mumbai",
            "area_description": "Downtown",
            "device_count": 5,
            "device_types": ["IP Camera"],
            "manufacturers": ["Hikvision"],
            "owner_types": {"government": 5},
            "nearby_news_headlines": [],
        }

        with patch("services.claude_service.DATABASE_PATH", db_path), \
             patch("services.claude_service.GROQ_API_KEY", ""):
            res = await generate_brief(req)
            assert res["cluster_id"] == "cluster_test_no_key"
            assert "not configured" in res["brief_text"]
            assert res["risk_level"] == "MEDIUM"
            assert res["from_cache"] is False

    @pytest.mark.asyncio
    async def test_generate_brief_caching_flow(self, tmp_path):
        db_path = str(tmp_path / "test_brief_cache.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_briefs (
                    cluster_id TEXT PRIMARY KEY,
                    city TEXT,
                    brief_text TEXT,
                    risk_level TEXT,
                    generated_at TEXT
                )
                """
            )
            await db.execute(
                "INSERT INTO risk_briefs VALUES (?, ?, ?, ?, ?)",
                ("cluster_cached", "Mumbai", "Cached brief content.", "HIGH", "2026-01-01T00:00:00Z"),
            )
            await db.commit()

        req = {
            "cluster_id": "cluster_cached",
            "city": "Mumbai",
            "area_description": "Downtown",
            "device_count": 5,
            "device_types": ["IP Camera"],
            "manufacturers": ["Hikvision"],
            "owner_types": {"government": 5},
            "nearby_news_headlines": [],
        }

        with patch("services.claude_service.DATABASE_PATH", db_path):
            res = await generate_brief(req)
            assert res["cluster_id"] == "cluster_cached"
            assert res["brief_text"] == "Cached brief content."
            assert res["risk_level"] == "HIGH"
            assert res["from_cache"] is True

    @pytest.mark.asyncio
    async def test_generate_brief_api_exception_fallback(self, tmp_path):
        db_path = str(tmp_path / "test_brief_err.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_briefs (
                    cluster_id TEXT PRIMARY KEY,
                    city TEXT,
                    brief_text TEXT,
                    risk_level TEXT,
                    generated_at TEXT
                )
                """
            )
            await db.commit()

        req = {
            "cluster_id": "cluster_err",
            "city": "Mumbai",
            "area_description": "Downtown",
            "device_count": 5,
            "device_types": ["IP Camera"],
            "manufacturers": ["Hikvision"],
            "owner_types": {"government": 5},
            "nearby_news_headlines": [],
        }

        with patch("services.claude_service.DATABASE_PATH", db_path), \
             patch("services.claude_service.GROQ_API_KEY", "mock_key"), \
             patch("services.claude_service.AsyncGroq", side_effect=Exception("API limit exceeded")):
            res = await generate_brief(req)
            assert res["cluster_id"] == "cluster_err"
            assert "temporarily unavailable" in res["brief_text"]
            assert res["risk_level"] == "MEDIUM"
            assert res["from_cache"] is False
