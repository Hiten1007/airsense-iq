import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
import yaml

if sys.platform == "win32":
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load yaml configuration."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def resolve_city_coordinates(city_name: str, config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Resolve city name to latitude, longitude, and timezone via Open-Meteo Geocoding API,
    or look up in local presets.
    """
    config = load_config(config_path)
    # Check presets first
    presets = config.get("preset_cities", [])
    for preset in presets:
        if preset["name"].lower() == city_name.strip().lower():
            return preset

    # Query geocoding API
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "results" in data and len(data["results"]) > 0:
            res = data["results"][0]
            return {
                "name": res.get("name", city_name),
                "country": res.get("country", ""),
                "latitude": res["latitude"],
                "longitude": res["longitude"],
                "timezone": res.get("timezone", "UTC")
            }
    except Exception as e:
        logger.warning(f"Geocoding lookup failed for '{city_name}': {e}. Falling back to default city.")

    # Fallback to default city in config
    return config["city"]


def fetch_air_quality_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = "Asia/Kolkata",
    variables: Optional[list] = None
) -> pd.DataFrame:
    """
    Fetch historical pollutant data from Open-Meteo Air Quality API.
    """
    if variables is None:
        variables = ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "carbon_monoxide"]

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(variables),
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone
    }

    logger.info(f"Fetching air quality data from {start_date} to {end_date}...")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "hourly" not in data:
        raise ValueError(f"Open-Meteo response missing 'hourly' payload: {data}")

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def fetch_weather_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = "Asia/Kolkata",
    variables: Optional[list] = None
) -> pd.DataFrame:
    """
    Fetch historical weather data from Open-Meteo Historical Archive API.
    """
    if variables is None:
        variables = [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m"
        ]

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(variables),
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone
    }

    logger.info(f"Fetching weather archive data from {start_date} to {end_date}...")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "hourly" not in data:
        raise ValueError(f"Open-Meteo archive response missing 'hourly' payload: {data}")

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def fetch_and_merge_historical_dataset(
    config_path: str = "config/config.yaml",
    save_raw: bool = True
) -> pd.DataFrame:
    """
    Fetch both air quality and weather data, merge on timestamp, and optionally cache to disk.
    """
    config = load_config(config_path)
    city_cfg = config["city"]
    data_cfg = config["data"]

    historical_days = data_cfg.get("historical_days", 365)
    end_dt = datetime.now() - timedelta(days=2)  # Open-Meteo archive typically has a 2-day finalization lag
    start_dt = end_dt - timedelta(days=historical_days)

    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    logger.info(f"Querying city: {city_cfg['name']} ({city_cfg['latitude']}, {city_cfg['longitude']})")
    
    aq_df = fetch_air_quality_data(
        latitude=city_cfg["latitude"],
        longitude=city_cfg["longitude"],
        start_date=start_date,
        end_date=end_date,
        timezone=city_cfg.get("timezone", "Asia/Kolkata"),
        variables=data_cfg.get("pollutant_variables")
    )

    weather_df = fetch_weather_data(
        latitude=city_cfg["latitude"],
        longitude=city_cfg["longitude"],
        start_date=start_date,
        end_date=end_date,
        timezone=city_cfg.get("timezone", "Asia/Kolkata"),
        variables=data_cfg.get("weather_variables")
    )

    merged_df = pd.merge(aq_df, weather_df, on="time", how="inner")
    merged_df.sort_values("time", inplace=True)
    merged_df.reset_index(drop=True, inplace=True)

    if save_raw:
        raw_path = data_cfg.get("raw_data_path", "data/raw/aqi_data.csv")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        merged_df.to_csv(raw_path, index=False)
        logger.info(f"Saved {len(merged_df)} raw records to {raw_path}")

    return merged_df


if __name__ == "__main__":
    df = fetch_and_merge_historical_dataset()
    print(f"Dataset shape: {df.shape}")
    print(df.head())
