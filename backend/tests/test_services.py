import pytest
from services.news_service import _geo_tag_article
from services.claude_service import _build_prompt

def test_geo_tag_article_keyword_match():
    """Test geo-tagging based on known keywords"""
    lat, lon, conf = _geo_tag_article("Crime in Dharavi", "A new CCTV...", "Mumbai")
    assert conf == "keyword-matched"
    assert lat == 19.0390
    assert lon == 72.8519

def test_geo_tag_article_city_level():
    """Test geo-tagging fallback to city level"""
    lat, lon, conf = _geo_tag_article("General news", "Nothing specific", "Mumbai")
    assert conf == "city-level"
    assert lat == 19.0760
    assert lon == 72.8777

def test_generate_risk_prompt():
    """Test the structure of the LLM prompt generator"""
    req = {
        "cluster_id": "test_cluster",
        "city": "Delhi",
        "area_description": "Test Area",
        "device_count": 5,
        "device_types": ["IP Camera"],
        "manufacturers": ["Hikvision"],
        "owner_types": {"government": 3, "commercial": 2},
        "nearby_news_headlines": ["Test News"]
    }
    prompt = _build_prompt(req)
    assert "Delhi" in prompt
    assert "5" in prompt
    assert "IP Camera" in prompt
    assert "Hikvision" in prompt
    assert "government" in prompt
    assert "Test News" in prompt
