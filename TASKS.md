# AQI Prediction CI/CD Pipeline - Project Roadmap & Task Tracker

## 📌 Project Overview
An end-to-end MLOps pipeline for predicting Air Quality Index (AQI) / PM2.5 levels with automated testing, continuous integration, model evaluation gates, continuous deployment, and an interactive geospatial map dashboard.

---

## 🏗️ Architecture Design Decisions
- **Target Cities**: Global coverage via Open-Meteo Geocoding API + preset hubs (Delhi, Mumbai, Bengaluru, London, New York, Tokyo).
- **Data Source**: Open-Meteo Air Quality & Weather API (Free, high-availability, no API key required, hourly historical & forecast data).
- **Prediction Target**: Next 24-hour PM2.5 / AQI regression.
- **Model Baseline & Candidate**: LightGBM regressor with atmospheric physics (wind vectors, ventilation proxy) and time-series lag features.
- **Evaluation Gate for CI/CD**: Model must outperform baseline metrics ($R^2 \ge 0.60$, $\text{RMSE} \le 50.0$, and beat previous champion within tolerance) on an unseen 30-day holdout test window before promotion.
- **CI/CD Platform**: GitHub Actions (Linting, Unit Tests, Data Validation, Automated Retraining, Model Evaluation & Artifact Packaging).
- **Frontend & Visualization**:
  - Interactive Leaflet.js Geospatial Radar Map with CartoDB Dark Matter tiles and pulsing AQI pins.
  - Chart.js 24-hour trajectory curve with dynamic gradient fills.
  - Zero-maintenance static publishing via **GitHub Pages**.

---

## 📋 Task Checklist

### Phase 1: System Design & Architecture Specification
- [x] Select data provider (Open-Meteo Air Quality & Weather API)
- [x] Define prediction objective (Next 24h AQI / PM2.5 forecasting)
- [x] Establish CI/CD trigger and gate strategy (Lint -> Test -> Train -> Metric Gate -> Deploy)
- [x] Create project task tracking system (`TASKS.md`)

### Phase 2: Project Scaffolding & Environment Setup
- [x] Initialize repository structure (`src/`, `tests/`, `.github/workflows/`, `config/`, `data/`, `models/`, `templates/`, `docs/`)
- [x] Define dependencies in `requirements.txt`
- [x] Create configuration management (`config/config.yaml` for preset cities, hyperparameters, thresholds)
- [x] Set up `.gitignore` and `.dockerignore`

### Phase 3: Data Ingestion & Preprocessing
- [x] Implement data fetcher client for Open-Meteo historical & forecast data (`src/data_loader.py`)
- [x] Add global city geocoding resolver (`src/data_loader.py:resolve_city_coordinates`)
- [x] Implement feature engineering: rolling averages, lag features ($t-1, t-2, t-24$), cyclical hour/month encoding, wind $U/V$ vectors, ventilation proxy (`src/features.py`)
- [x] Seed dataset with 8,784 historical hourly observations

### Phase 4: Model Development, Training & Evaluation
- [x] Implement LightGBM regressor with tabular time-series features (`src/train.py`)
- [x] Implement evaluation metrics computation: MAE, RMSE, $R^2$, mean bias (`src/evaluate.py`)
- [x] Implement automated Champion vs. Challenger model gating check (`src/gate.py`)
- [x] Persist model artifacts, feature schema, and training metadata (`models/champion/model.joblib`)
- [x] Verified model performance: $R^2 = 0.9717$, $\text{RMSE} = 5.65$ on 30-day holdout test set

### Phase 5: CI/CD Pipeline Automation (GitHub Actions)
- [x] Create CI workflow: code formatting & linting (`flake8`) + unit tests (`pytest`) (`.github/workflows/ci.yml`)
- [x] Create Continuous Training (CT) workflow with weekly schedule (`.github/workflows/ct.yml`)
- [x] Add automated evaluation gate step (`gate.py`) to CT workflow with artifact promotion and auto-commit
- [x] Create CD workflow: build and publish production Docker image to GitHub Container Registry & trigger webhooks (`.github/workflows/cd.yml`)
- [x] Create GitHub Pages deployment workflow (`.github/workflows/pages.yml`)
- [x] Maintain passing test suite across all feature, model, and API test suites

### Phase 6: Geospatial Dashboard & Serving Delivery
- [x] Design vibrant, modern UI with Leaflet.js interactive dark radar map (`templates/index.html`)
- [x] Add 24-hour Chart.js trajectory curve with dynamic gradient fills based on AQI risk
- [x] Implement global multi-city search + quick preset buttons (Delhi, Mumbai, Bengaluru, London, New York, Tokyo)
- [x] Implement live coordinates inspector: click anywhere on the globe to predict
- [x] Create static generator script (`src/generate_static_page.py`) to publish directly to GitHub Pages (`docs/`)
- [x] Update production `Dockerfile` with embedded templates
