"""
test_nl_query_router.py
=========================
Tests for Module H — natural-language map query parsing. Groq calls are
mocked (never hits the real API in tests) so these verify the sanitization/
fallback contract, not live LLM output quality (that was verified manually —
see session notes). The fallback path (no key / parse failure) is exercised
for real since it needs no network.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from routes.nl_query_router import router, _sanitize, _extract_json


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _mock_groq_response(payload: dict):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    return response


class TestSanitize:
    def test_valid_city_and_owner_pass_through(self):
        result = _sanitize({"auth_required": False, "has_cve": True, "owner_type": "government", "city": "Delhi", "search_text": "x"})
        assert result == {
            "auth_required": False, "has_cve": True, "owner_type": "government",
            "city": "Delhi", "search_text": "x", "explanation": "",
        }

    def test_invalid_city_dropped(self):
        result = _sanitize({"city": "Narnia"})
        assert result["city"] is None

    def test_invalid_owner_type_dropped(self):
        result = _sanitize({"owner_type": "alien"})
        assert result["owner_type"] is None

    def test_auth_required_true_is_ignored(self):
        """Schema only supports auth_required=False (open) or None — 'true' isn't a meaningful filter value here."""
        result = _sanitize({"auth_required": True})
        assert result["auth_required"] is None

    def test_search_text_truncated(self):
        result = _sanitize({"search_text": "x" * 500})
        assert len(result["search_text"]) == 100


class TestExtractJson:
    def test_plain_json(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced_json(self):
        assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_with_surrounding_prose(self):
        assert _extract_json('Here is the filter: {"a": 1} hope that helps!') == {"a": 1}

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json("no json here")


class TestNLQueryEndpoint:
    @pytest.mark.asyncio
    async def test_empty_query_returns_fallback_without_calling_groq(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/api/nl-query", json={"query": "   "})
        assert res.status_code == 200
        data = res.json()
        assert data["parsed_by_ai"] is False

    @pytest.mark.asyncio
    async def test_successful_parse_returns_sanitized_filter(self, app):
        mock_payload = {
            "auth_required": False, "has_cve": True, "owner_type": "government",
            "city": "Delhi", "search_text": "", "explanation": "test",
        }
        with patch("routes.nl_query_router.GROQ_API_KEY", "fake-key-for-test"):
            with patch("groq.AsyncGroq") as MockGroq:
                MockGroq.return_value.chat.completions.create = AsyncMock(return_value=_mock_groq_response(mock_payload))
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    res = await client.post("/api/nl-query", json={"query": "unauthenticated government cameras in Delhi with CVEs"})
        assert res.status_code == 200
        data = res.json()
        assert data["parsed_by_ai"] is True
        assert data["city"] == "Delhi"
        assert data["owner_type"] == "government"
        assert data["auth_required"] is False
        assert data["has_cve"] is True

    @pytest.mark.asyncio
    async def test_groq_failure_falls_back_gracefully(self, app):
        with patch("routes.nl_query_router.GROQ_API_KEY", "fake-key-for-test"):
            with patch("groq.AsyncGroq") as MockGroq:
                MockGroq.return_value.chat.completions.create = AsyncMock(side_effect=Exception("network down"))
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    res = await client.post("/api/nl-query", json={"query": "hikvision cameras"})
        assert res.status_code == 200
        data = res.json()
        assert data["parsed_by_ai"] is False
        assert data["search_text"] == "hikvision cameras"

    @pytest.mark.asyncio
    async def test_no_api_key_falls_back_without_network_call(self, app):
        with patch("routes.nl_query_router.GROQ_API_KEY", ""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post("/api/nl-query", json={"query": "hikvision cameras"})
        assert res.status_code == 200
        data = res.json()
        assert data["parsed_by_ai"] is False
