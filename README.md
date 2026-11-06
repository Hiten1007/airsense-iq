# 🌍 AirSense IQ • Planetary Air Quality CI/CD & MLOps Platform

[![CI - Lint & Unit Tests](https://github.com/Hiten1007/airsense-iq/actions/workflows/ci.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/ci.yml)
[![CT - Automated Retraining](https://github.com/Hiten1007/airsense-iq/actions/workflows/ct.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/ct.yml)
[![CD - Package & Deploy](https://github.com/Hiten1007/airsense-iq/actions/workflows/cd.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/cd.yml)
[![Pages - Live Map Dashboard](https://github.com/Hiten1007/airsense-iq/actions/workflows/pages.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/pages.yml)

An enterprise-grade, end-to-end MLOps system that forecasts urban Air Quality Index (AQI) and PM2.5 levels using atmospheric physics and machine learning. Featuring **Continuous Integration (CI)**, **Continuous Training (CT)** with automated Champion vs. Challenger quality gating, **Continuous Deployment (CD)** via Docker and FastAPI, and a **Geospatial Interactive Radar Map Dashboard** deployable to **GitHub Pages**.

---

## 🗺️ Interactive Geospatial Dashboard Preview

- **Leaflet.js Dark Radar Map**: CartoDB Dark Matter tiles, glowing pulsing pins for current AQI risk, and smooth animated pan/zoom.
- **Global Multi-City Search**: Search any city on Earth via Open-Meteo Geocoding, or click anywhere on the globe to inspect coordinates.
- **24-Hour Predictive Trajectory Curve**: Smooth Chart.js area chart with dynamic gradient fills reflecting AQI risk bands.
- **Atmospheric Physics Telemetry**: Real-time display of wind speed/direction, ventilation index, humidity, surface pressure, and secondary pollutants ($\text{PM}_{10}, \text{NO}_2, \text{O}_3, \text{CO}$).

---

## 🏛️ System Architecture

```
                    ┌─────────────────────────┐
                    │  Open-Meteo Weather,    │
                    │   Air Quality & Geo     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                     [Data Ingestion Engine]
                                 │
                                 ▼
                   [Physics & Lag Feature Store]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [Continuous Integration]        [Continuous Training (CT)]
        • Flake8 code linting           • Automated weekly cron
        • Pytest test suites            • LightGBM regressor training
        • Data contract validation      • 30-day holdout validation
                 │                               │
                 │                               ▼
                 │                 [Champion vs. Challenger Gate]
                 │                  ├── Challenger beats Champion?
                 │                  └── R² >= 0.60 & RMSE <= 50.0
                 │                               │
                 │                 ┌─────────────┴─────────────┐
                 │                 ▼                           ▼
                 │            [✅ PROMOTE]               [❌ REJECT]
                 │                 │                     Keeps Champion
                 ▼                 ▼
          ┌───────────────────────────────────┐
          │     Continuous Deployment (CD)    │
          │  • GHCR Docker Container Build    │
          │  • FastAPI REST Endpoints         │
          │  • GitHub Pages Static Export     │
          └───────────────────────────────────┘
```

---

## 📂 Project Directory Structure

```
c:\AQI_Predict
├── .github/
│   └── workflows/
│       ├── ci.yml             # Linting and pytest test automation on PR/Push
│       ├── ct.yml             # Weekly automated retraining and model quality gating
│       ├── cd.yml             # Docker packaging and deployment dispatch
│       └── pages.yml          # Automated GitHub Pages static dashboard publishing
├── config/
│   └── config.yaml            # Single source of truth (preset hubs, coordinates, hyperparams)
├── data/
│   ├── raw/                   # Ingested 1-2 year hourly API payloads (cached)
│   ├── processed/             # Engineered feature matrices & holdout sets
│   └── latest_predictions.json# Real-time cached 24h predictions
├── docs/                      # Generated static website for GitHub Pages hosting
│   ├── index.html
│   └── .nojekyll
├── models/
│   ├── champion/              # Production-verified Champion model and metrics
│   │   ├── model.joblib
│   │   └── metrics.json
│   ├── candidate_model.joblib # Newly trained Challenger model
│   ├── feature_names.json     # Feature schema contract for inference validation
│   └── metrics.json           # Candidate evaluation metrics
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # Open-Meteo historical, real-time & geocoding client
│   ├── features.py            # Physics (wind vectors, ventilation) & lag features
│   ├── train.py               # Model training (LightGBM regressor)
│   ├── evaluate.py            # Model scoring (R², RMSE, MAE, Bias)
│   ├── gate.py                # Automated Champion vs. Challenger promotion gate
│   ├── predict.py             # Multi-city inference engine & live 24h forecasting
│   ├── api.py                 # FastAPI production REST service & dashboard host
│   └── generate_static_page.py# Builds static dashboard for GitHub Pages
├── templates/
│   └── index.html             # Vibrant, human-designed dark Leaflet map dashboard
├── tests/
│   ├── test_features.py       # Time-series transforms, lag integrity, non-leakage
│   ├── test_model.py          # Model evaluation thresholds & AQI categorization
│   └── test_api.py            # FastAPI endpoint status, dashboard & response schemas
├── Dockerfile                 # Production container definition
├── requirements.txt           # Python dependencies
├── TASKS.md                   # MLOps pipeline roadmap & milestone checklist
└── README.md
```

---

## 🚀 Quickstart & Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Interactive Map & API
```bash
uvicorn src.api:app --reload --port 8000
```
Open in browser:
- 🗺️ **Interactive Radar Map Dashboard**: `http://localhost:8000/`
- 📑 **Swagger REST Documentation**: `http://localhost:8000/docs`

### 3. Generate Static GitHub Pages Site
```bash
python src/generate_static_page.py
```
This builds `./docs/index.html` ready for 100% free hosting on GitHub Pages!

---

## 🧪 Automated Testing
```bash
pytest -v tests/
```

---

## 🌐 Deploying to GitHub Pages

1. Push your repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: complete aqi mlops pipeline with interactive map"
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. In your GitHub repository:
   - Go to **Settings > Pages**.
   - Under **Build and deployment > Source**, choose **GitHub Actions**.
3. The included `.github/workflows/pages.yml` workflow will automatically trigger, build the static site, and publish it to:
   👉 `https://Hiten1007.github.io/airsense-iq/`
