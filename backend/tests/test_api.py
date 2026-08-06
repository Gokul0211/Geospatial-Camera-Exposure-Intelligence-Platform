import pytest
from httpx import AsyncClient, ASGITransport
from main import app

# Use pytest-asyncio to handle async tests
pytestmark = pytest.mark.asyncio

async def test_health_check():
    """Test the health check endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"



async def test_get_stats_valid_city():
    """Test fetching surveillance stats for a valid city"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/stats?city=Mumbai")
        assert response.status_code == 200
        data = response.json()
        assert "total_devices" in data
        assert "by_owner" in data
        assert "by_type" in data
        assert "surveillance_score" in data
        # Ensure telecom and government are tracked
        assert "telecom" in data["by_owner"]
        assert "government" in data["by_owner"]

async def test_get_stats_invalid_city():
    """Test fetching surveillance stats for an unsupported city"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/stats?city=Gotham")
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

async def test_get_devices():
    """Test fetching GeoJSON device data"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/devices?city=Mumbai")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert isinstance(data["features"], list)
        
        # Verify feature structure if any exist
        if len(data["features"]) > 0:
            feature = data["features"][0]
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature
            assert "owner_type" in feature["properties"]

async def test_get_news():
    """Test fetching regional news feed"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/news?city=Mumbai")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "total" in data
        assert isinstance(data["articles"], list)
