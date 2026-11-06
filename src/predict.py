import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import joblib
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_config, resolve_city_coordinates
from src.features import build_feature_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_champion_model(config_path: str = "config/config.yaml"):
    """Load the current deployed Champion model and feature list."""
    config = load_config(config_path)
    champion_path = config["model"]["champion_model_path"]
    model_dir = config["model"]["model_dir"]
    features_path = os.path.join(model_dir, "feature_names.json")

    if not os.path.exists(champion_path):
        raise FileNotFoundError(f"Champion model not found at {champion_path}. Run training & gate first.")
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Feature schema not found at {features_path}.")

    model = joblib.load(champion_path)
    with open(features_path, "r") as f:
        feature_names = json.load(f)

    return model, feature_names, config


def predict_from_dataframe(
    df: pd.DataFrame,
    config_path: str = "config/config.yaml"
) -> List[Dict[str, Any]]:
    """
    Run prediction on a pre-processed or feature-engineered DataFrame.
    """
    model, feature_names, _ = load_champion_model(config_path)

    # Check if feature engineering needs to be run
    missing_features = [f for f in feature_names if f not in df.columns]
    if missing_features:
        logger.info(f"Running feature pipeline for inference ({len(missing_features)} features to compute)...")
        df_featured = build_feature_pipeline(df, drop_na=False)
        df_featured = df_featured.ffill().bfill()
    else:
        df_featured = df

    X = df_featured[feature_names]
    preds = model.predict(X)

    results = []
    for idx, pred in enumerate(preds):
        time_val = str(df_featured.iloc[idx]["time"]) if "time" in df_featured.columns else f"t+{idx}h"
        results.append({
            "timestamp": time_val,
            "predicted_pm2_5": round(float(pred), 2),
            "aqi_category": categorize_pm2_5(float(pred))
        })

    return results


def categorize_pm2_5(pm2_5: float) -> str:
    """Classify PM2.5 concentration into standard AQI category."""
    if pm2_5 <= 30:
        return "Good"
    elif pm2_5 <= 60:
        return "Satisfactory"
    elif pm2_5 <= 90:
        return "Moderate"
    elif pm2_5 <= 120:
        return "Poor"
    elif pm2_5 <= 250:
        return "Very Poor"
    else:
        return "Severe"


def generate_live_forecast(
    city_name: Optional[str] = None,
    config_path: str = "config/config.yaml"
) -> Dict[str, Any]:
    """
    Fetch the most recent 48 hours of live data from Open-Meteo for any city,
    construct physics & lag features, and predict the upcoming 24-hour AQI trajectory.
    """
    config = load_config(config_path)
    data_cfg = config["data"]

    if city_name:
        city_info = resolve_city_coordinates(city_name, config_path)
    else:
        city_info = config["city"]

    # Use Open-Meteo Live API
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_params = {
        "latitude": city_info["latitude"],
        "longitude": city_info["longitude"],
        "hourly": ",".join(data_cfg["pollutant_variables"]),
        "past_days": 2,
        "forecast_days": 1,
        "timezone": city_info.get("timezone", "Asia/Kolkata")
    }

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": city_info["latitude"],
        "longitude": city_info["longitude"],
        "hourly": ",".join(data_cfg["weather_variables"]),
        "past_days": 2,
        "forecast_days": 1,
        "timezone": city_info.get("timezone", "Asia/Kolkata")
    }

    logger.info(f"Fetching real-time conditions for {city_info['name']} ({city_info['latitude']}, {city_info['longitude']})...")
    if sys.platform == "win32":
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass

    try:
        aq_res = requests.get(aq_url, params=aq_params, timeout=15)
        aq_res.raise_for_status()
        aq_resp = aq_res.json()

        weather_res = requests.get(weather_url, params=weather_params, timeout=15)
        weather_res.raise_for_status()
        weather_resp = weather_res.json()

        if "hourly" not in aq_resp or "hourly" not in weather_resp:
            raise ValueError(f"Incomplete hourly payload from Open-Meteo: aq={aq_resp.get('error')}, weather={weather_resp.get('error')}")

        aq_df = pd.DataFrame(aq_resp["hourly"])
        weather_df = pd.DataFrame(weather_resp["hourly"])

        merged = pd.merge(aq_df, weather_df, on="time", how="inner")
        merged["time"] = pd.to_datetime(merged["time"])

        # Extract current weather conditions (latest timestamp)
        latest_row = merged.iloc[-25] if len(merged) >= 25 else merged.iloc[-1]
        current_metrics = {
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

        predictions = predict_from_dataframe(merged, config_path)
        forecast_24h = predictions[-24:]

        payload = {
            "city": city_info["name"],
            "country": city_info.get("country", ""),
            "latitude": city_info["latitude"],
            "longitude": city_info["longitude"],
            "timezone": city_info.get("timezone", "UTC"),
            "generated_at": datetime.now().isoformat(),
            "current_weather": current_metrics,
            "forecasts": forecast_24h
        }

        # Cache default city prediction if not custom city
        if not city_name or city_name.lower() == config["city"]["name"].lower():
            out_path = config.get("serving", {}).get("predictions_output_path", "data/latest_predictions.json")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(payload, f, indent=2)

        logger.info(f"Live forecast generated for {city_info['name']}")
        return payload

    except Exception as e:
        logger.warning(f"Live API query failed ({e}). Checking for cached payload fallback...")
        cached_path = config.get("serving", {}).get("predictions_output_path", "data/latest_predictions.json")
        if os.path.exists(cached_path):
            with open(cached_path, "r") as f:
                cached_data = json.load(f)
                cached_data["city"] = city_info["name"]
                cached_data["country"] = city_info.get("country", "")
                cached_data["latitude"] = city_info["latitude"]
                cached_data["longitude"] = city_info["longitude"]
                return cached_data
        raise e


if __name__ == "__main__":
    result = generate_live_forecast()
    print(f"City: {result['city']}, Country: {result['country']}")
    print("Next 24h Predictions sample:")
    for f in result["forecasts"][:5]:
        print(f)
