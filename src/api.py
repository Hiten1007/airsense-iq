import os
import sys
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_config, resolve_city_coordinates
from src.predict import predict_from_dataframe, generate_live_forecast
import pandas as pd
import requests

app = FastAPI(
    title="AeroCast Air Quality (AQI) CI/CD & MLOps Service",
    description="Production-grade geospatial air quality forecasting service powered by LightGBM and ECMWF reanalysis.",
    version="1.0.0"
)


class AQIPredictionItem(BaseModel):
    timestamp: str
    predicted_pm2_5: float
    aqi_category: str


class LiveForecastResponse(BaseModel):
    city: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    timezone: str
    generated_at: str
    current_weather: Optional[Dict[str, Any]] = None
    forecasts: List[AQIPredictionItem]


class HealthResponse(BaseModel):
    status: str
    city: str
    champion_model_present: bool
    champion_metrics: Optional[Dict[str, Any]] = None


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the interactive AeroCast Geospatial Dashboard."""
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard template not found</h1>", status_code=404)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check and model status verification for Docker & cloud orchestrators."""
    config = load_config()
    champion_path = config["model"]["champion_model_path"]
    metrics_path = os.path.join(os.path.dirname(champion_path), "metrics.json")

    champion_exists = os.path.exists(champion_path)
    metrics = None
    if champion_exists and os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics = json.load(f)

    return {
        "status": "healthy" if champion_exists else "initializing",
        "city": config["city"]["name"],
        "champion_model_present": champion_exists,
        "champion_metrics": metrics
    }


@app.get("/cities/presets")
def get_preset_cities():
    """Return preset popular global cities with coordinates."""
    config = load_config()
    return config.get("preset_cities", [])


@app.get("/forecast/next24h", response_model=LiveForecastResponse)
def get_live_24h_forecast(
    city: Optional[str] = Query(None, description="City name to forecast (e.g., Delhi, Mumbai, London)"),
    lat: Optional[float] = Query(None, description="Optional custom latitude"),
    lon: Optional[float] = Query(None, description="Optional custom longitude")
):
    """
    Fetch real-time atmospheric and pollutant vectors, run physics feature pipeline,
    and return predicted 24h PM2.5 levels with health categories.
    """
    try:
        config = load_config()

        # If custom coordinates provided directly via map click
        if lat is not None and lon is not None:
            # Query reverse geocode / elevation name if possible
            city_name = f"Loc ({lat:.2f}, {lon:.2f})"
            data_cfg = config["data"]

            aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            weather_url = "https://api.open-meteo.com/v1/forecast"
            tz = "auto"

            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                pass

            aq_resp = requests.get(aq_url, params={
                "latitude": lat, "longitude": lon,
                "hourly": ",".join(data_cfg["pollutant_variables"]),
                "past_days": 2, "forecast_days": 1, "timezone": tz
            }, timeout=20).json()

            weather_resp = requests.get(weather_url, params={
                "latitude": lat, "longitude": lon,
                "hourly": ",".join(data_cfg["weather_variables"]),
                "past_days": 2, "forecast_days": 1, "timezone": tz
            }, timeout=20).json()

            aq_df = pd.DataFrame(aq_resp["hourly"])
            weather_df = pd.DataFrame(weather_resp["hourly"])
            merged = pd.merge(aq_df, weather_df, on="time", how="inner")
            merged["time"] = pd.to_datetime(merged["time"])

            latest_row = merged.iloc[-25] if len(merged) >= 25 else merged.iloc[-1]
            current_weather = {
                "temperature_2m": float(latest_row.get("temperature_2m", 0.0)),
                "relative_humidity_2m": float(latest_row.get("relative_humidity_2m", 0.0)),
                "wind_speed_10m": float(latest_row.get("wind_speed_10m", 0.0)),
                "wind_direction_10m": float(latest_row.get("wind_direction_10m", 0.0)),
                "surface_pressure": float(latest_row.get("surface_pressure", 0.0)),
                "pm10": float(latest_row.get("pm10", 0.0)),
                "nitrogen_dioxide": float(latest_row.get("nitrogen_dioxide", 0.0)),
                "ozone": float(latest_row.get("ozone", 0.0)),
                "carbon_monoxide": float(latest_row.get("carbon_monoxide", 0.0)),
            }

            predictions = predict_from_dataframe(merged)
            from datetime import datetime
            return {
                "city": city_name,
                "country": "Custom Map Point",
                "latitude": lat,
                "longitude": lon,
                "timezone": aq_resp.get("timezone", "UTC"),
                "generated_at": datetime.now().isoformat(),
                "current_weather": current_weather,
                "forecasts": predictions[-24:]
            }

        # Otherwise standard city name query
        result = generate_live_forecast(city_name=city)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict")
def predict_custom_features(data: List[Dict[str, Any]]):
    """Predict AQI/PM2.5 on arbitrary custom feature batches."""
    try:
        if not data:
            raise HTTPException(status_code=400, detail="Payload cannot be empty.")
        df = pd.DataFrame(data)
        predictions = predict_from_dataframe(df)
        return {"predictions": predictions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
