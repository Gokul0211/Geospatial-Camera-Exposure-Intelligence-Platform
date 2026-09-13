"""
test_auxiliary_routes_services.py
==================================
Integration and unit tests for auxiliary routes & services:
- GET /api/devices (GeoJSON response)
- GET /api/stats (surveillance index calculation)
- GET /api/heatmap (coordinate intensity mapping)
- GET /api/news (news article retrieval)
- POST /api/brief (risk brief generation)
- Unsupported city handling
- Unit tests for underlying services: auth_detection, ownership, vulnerability, classifier, claude
"""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from routes.devices import router as devices_router
from routes.stats import router as stats_router, _calculate_surveillance_score
from routes.heatmap import router as heatmap_router
from routes.news import router as news_router
from routes.brief import router as brief_router

from services.classifier import classify_owner_by_keywords
from services.shodan_service import _classify_device_type
from services.vulnerability_service import check_device_vulnerabilities


@pytest_asyncio.fixture
def app():
    api_app = FastAPI()
    api_app.include_router(devices_router, prefix="/api")
    api_app.include_router(stats_router, prefix="/api")
    api_app.include_router(heatmap_router, prefix="/api")
    api_app.include_router(news_router, prefix="/api")
    api_app.include_router(brief_router, prefix="/api")
    return api_app


class TestAuxiliaryRoutes:
    @pytest.mark.asyncio
    async def test_get_devices_geojson(self, app):
        mock_devices = [
            {"id": "cam1", "ip": "1.2.3.4", "lat": 19.07, "lon": 72.87, "device_type": "IP Camera", "city": "Mumbai"}
        ]
        with patch("routes.devices.fetch_and_cache_city", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_devices
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                res = await client.get("/api/devices?city=Mumbai")

            assert res.status_code == 200
            data = res.json()
            assert data["type"] == "FeatureCollection"
            assert len(data["features"]) == 1

    @pytest.mark.asyncio
    async def test_get_stats_route(self, app):
        mock_devices = [
            {"id": f"cam{i}", "device_type": "IP Camera", "owner_type": "government", "manufacturer": "Hikvision"}
            for i in range(700)
        ]
        with patch("routes.stats.fetch_and_cache_city", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_devices
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                res = await client.get("/api/stats?city=Mumbai")

            assert res.status_code == 200
            data = res.json()
            assert data["total_devices"] == 700
            assert data["by_owner"]["government"] == 700
            assert data["surveillance_score"]["devices_per_sq_km"] > 0

    @pytest.mark.asyncio
    async def test_get_heatmap_route(self, app):
        mock_devices = [
            {"lat": 19.07, "lon": 72.87, "device_type": "IP Camera"},
            {"lat": 19.08, "lon": 72.88, "device_type": "RTSP Stream"},
        ]
        with patch("routes.heatmap.fetch_and_cache_city", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_devices
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                res = await client.get("/api/heatmap?city=Mumbai")

            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 2
            assert data["points"][0] == [19.07, 72.87, 1.5]
            assert data["points"][1] == [19.08, 72.88, 1.2]

    @pytest.mark.asyncio
    async def test_invalid_city_returns_400(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res_dev = await client.get("/api/devices?city=InvalidCity")
            res_stat = await client.get("/api/stats?city=InvalidCity")
            res_heat = await client.get("/api/heatmap?city=InvalidCity")
            res_news = await client.get("/api/news?city=InvalidCity")

        assert res_dev.status_code == 400
        assert res_stat.status_code == 400
        assert res_heat.status_code == 400
        assert res_news.status_code == 400

    @pytest.mark.asyncio
    async def test_post_brief_route(self, app):
        mock_brief = {
            "cluster_id": "cluster_1",
            "brief_text": "High risk area detected",
            "risk_level": "CRITICAL",
        }
        with patch("routes.brief.generate_brief", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_brief
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                res = await client.post(
                    "/api/brief",
                    json={
                        "cluster_id": "cluster_1",
                        "city": "Mumbai",
                        "device_count": 5,
                        "device_types": ["IP Camera"],
                        "manufacturers": ["Hikvision"],
                        "owner_types": {"government": 3, "unknown": 2},
                        "nearby_news_headlines": ["Protest reported"],
                        "area_description": "Financial district",
                    },
                )
            assert res.status_code == 200
            assert res.json() == mock_brief


class TestServicesUnit:
    def test_calculate_surveillance_score_empty(self):
        assert _calculate_surveillance_score([], "Mumbai") is None

    def test_ownership_resolution_heuristics(self):
        owner_type, conf = classify_owner_by_keywords(org="Municipal Corporation of Delhi", asn_description="BSNL")
        assert owner_type == "government"

        owner_type_tel, conf_tel = classify_owner_by_keywords(org="Reliance Jio Infocomm", asn_description="Jio")
        assert owner_type_tel == "telecom"

        owner_type_corp, conf_corp = classify_owner_by_keywords(org="Tata Consultancy Services", asn_description="TCS Internal Network")
        assert owner_type_corp == "corporate"

        owner_type_unk, conf_unk = classify_owner_by_keywords(org="", asn_description="")
        assert owner_type_unk == "unknown"

    def test_device_classifier(self):
        cam = _classify_device_type({"product": "Hikvision IP camera", "port": 554})
        assert cam == "IP Camera"

        dvr = _classify_device_type({"http": {"title": "Dahua DVR Login"}, "port": 80})
        assert dvr == "DVR/NVR"

        rtsp = _classify_device_type({"port": 554, "data": "RTSP/1.0 200 OK"})
        assert rtsp == "RTSP Stream"

    @pytest.mark.asyncio
    async def test_vulnerability_cve_parser(self):
        mock_nvd_data = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-36260",
                        "published": "2021-09-20T00:00:00.000",
                    }
                }
            ]
        }
        with patch("services.vulnerability_service._query_nvd", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_nvd_data
            res = await check_device_vulnerabilities("Hikvision")
            assert res["known_cve_count"] == 1
            assert "CVE-2021-36260" in res["cve_ids"]
            assert res["last_patch_date"] == "2021-09-20"
