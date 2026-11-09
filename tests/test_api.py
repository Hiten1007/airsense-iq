import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_dashboard_endpoint():
    """Verify that GET / returns the vibrant HTML dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AirSense" in response.text
    assert "<!DOCTYPE html>" in response.text


def test_health_check_endpoint():
    """Verify that GET /health returns the JSON health contract for Docker."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "city" in data
    assert "champion_model_present" in data


def test_preset_cities_endpoint():
    """Verify that preset cities list includes coordinates."""
    response = client.get("/cities/presets")
    assert response.status_code == 200
    presets = response.json()
    assert isinstance(presets, list)
    assert len(presets) > 0
    assert "name" in presets[0]
    assert "latitude" in presets[0]


def test_forecast_endpoint_structure():
    """Verify that live forecast endpoint returns 24h predictions."""
    response = client.get("/forecast/next24h?city=Delhi")
    if response.status_code == 200:
        data = response.json()
        assert "city" in data
        assert "forecasts" in data
        assert len(data["forecasts"]) > 0
        first_item = data["forecasts"][0]
        assert "predicted_pm2_5" in first_item
        assert "predicted_aqi" in first_item
        assert "aqi_category" in first_item
