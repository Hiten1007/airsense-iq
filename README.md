# 🌍 AirSense IQ • Planetary Air Quality CI/CD & MLOps Platform

[![CI - Lint, Test & Security Audit](https://github.com/Hiten1007/airsense-iq/actions/workflows/ci.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/ci.yml)
[![Hourly Sync & Keep-Alive](https://github.com/Hiten1007/airsense-iq/actions/workflows/hourly-sync.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/hourly-sync.yml)
[![CD - Package, Scan & Deploy](https://github.com/Hiten1007/airsense-iq/actions/workflows/cd.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/cd.yml)
[![Pages - Live Map Dashboard](https://github.com/Hiten1007/airsense-iq/actions/workflows/pages.yml/badge.svg)](https://github.com/Hiten1007/airsense-iq/actions/workflows/pages.yml)
[![Security: Bandit SAST](https://img.shields.io/badge/Security-Bandit%20SAST%20Clean-success.svg)](https://github.com/PyCQA/bandit)
[![Dependencies: pip--audit](https://img.shields.io/badge/Dependencies-pip--audit%20Clean-success.svg)](https://github.com/pypa/pip-audit)

An enterprise-grade, end-to-end MLOps system that forecasts urban Air Quality Index (AQI) and PM2.5 levels using atmospheric physics and machine learning. Featuring **Continuous Integration (CI)**, **Continuous Training (CT)** with automated Champion vs. Challenger quality gating, **Continuous Deployment (CD)** via Docker and FastAPI, **Security SAST & CVE Auditing**, **Jenkins Pipeline Integration**, and an **Interactive Geospatial Radar Dashboard** with automated 24h rolling updates.

---

## 📑 Core Documentation Guides
- 📘 **[Complete CI/CD, Jenkins & Security Architecture Guide](docs/CI_CD_JENKINS_SECURITY_GUIDE.md)**: Detailed technical specifications for Tasks 3, 4, and 5, including step-by-step zero-cost Jenkins integration via Smee.io / Cloudflare Tunnel.
- 📋 **[Milestone & Requirements Tracker](TASKS.md)**: MLOps roadmap and architecture decision records.

---

## 🗺️ Interactive Geospatial Dashboard Preview

- **Leaflet.js Dark Radar Map**: ESRI World Dark Canvas tiles, glowing pulsing pins for current AQI risk, and smooth animated pan/zoom.
- **Global Multi-City Search**: Search any city on Earth via Open-Meteo Geocoding, or click anywhere on the globe to inspect coordinates.
- **24-Hour Moving Rolling Trajectory**: Dual telemetry comparing real ground truth (past observations) vs. LightGBM model forecasts, complete with vertical `▼ NOW` demarcation line and radar pulse beacon.
- **Horizon View Filters**: Toggle between **Rolling 24h (Now ± 12h)**, **Past 24h Reality**, and **Next 24h Forecast**.
- **Official CPCB Multi-Pollutant Index**: Implements the Indian Central Pollution Control Board sub-index piecewise formula with exact truncation and rounding.

---

## 🏛️ Pipeline & Security Architecture

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
        • Pytest (14 test suites)       • LightGBM regressor training
        • Bandit SAST Security Scan     • 30-day holdout validation
        • pip-audit CVE check           • Quality Gate: R² >= 0.60
                 │                               │
                 │                 ┌─────────────┴─────────────┐
                 │                 ▼                           ▼
                 │            [✅ PROMOTE]               [❌ REJECT]
                 │                 │                     Keeps Champion
                 │                 ▼
                 │    [Hourly Telemetry Sync]
                 │     • Live 24h forecast update
                 │     • Pings Render server to keep warm
                 │     • Pushes fresh JSON to GitHub Pages
                 ▼                 │
     [Jenkins Pipeline / CD] ◄─────┘
      • Docker Build & Trivy Scan
      • Render Deploy Webhook
```

---

## 🛡️ Task 4: Security Integration & Performance Analysis

| Security & Quality Gate | Tool | Status | Findings |
|---|---|---|---|
| **Static Code Analysis (SAST)** | `Bandit v1.9.4` | **PASSED** | **0 Issues** (0 High, 0 Medium, 0 Low) |
| **Code Style & Complexity** | `Flake8 v6.1.0` | **PASSED** | Clean syntax, max complexity <= 10 |
| **Dependency Vulnerability Scan** | `pip-audit v2.10.1` | **PASSED** | **0 CVEs** across all dependencies |
| **Container Vulnerability Scan** | `Trivy` | **CONFIGURED**| Audits OS & library CVEs in CD & Jenkins |
| **Model Evaluation Metrics** | `scikit-learn` | **PASSED** | $R^2 = 0.9717$, $\text{RMSE} = 5.65$ µg/m³ |

Run security scans locally:
```bash
# Static Application Security Testing
python -m bandit -r src/

# Dependency CVE Audit
python -m pip_audit -r requirements.txt
```

---

## ⚙️ Task 3: Jenkins Integration (100% Free / Zero Cloud Cost)

A production-ready declarative **`Jenkinsfile`** is included at repository root. You can run Jenkins live on your local machine with automatic GitHub webhook triggers at zero cost:

1. **Start Jenkins in Docker**:
   ```bash
   docker compose -f docker-compose.jenkins.yml up -d
   ```
2. **Expose Free Webhook Relay (Smee.io)**:
   ```bash
   smee --url https://smee.io/<your-channel-id> --target http://localhost:8080/github-webhook/
   ```
3. **Configure GitHub Webhook**:
   - In GitHub Repo > **Settings** > **Webhooks**, set Payload URL to your Smee URL.
   - Pushing code to GitHub will now automatically trigger the full 8-stage Jenkins pipeline locally!

See the [Complete Jenkins Setup Guide](docs/CI_CD_JENKINS_SECURITY_GUIDE.md#3c-jenkins-pipeline-configuration--zero-cost-live-integration) for step-by-step instructions.

---

## 🚀 Quickstart & Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
pytest -v tests/
```

### 3. Start API & Dashboard Locally
```bash
# Option A: Python Uvicorn
uvicorn src.api:app --reload --port 8000

# Option B: Docker Compose
docker compose up -d
```
Open in browser:
- 🗺️ **Interactive Radar Dashboard**: `http://localhost:8000/`
- 📑 **Swagger OpenAPI Docs**: `http://localhost:8000/docs`

---

## 🌐 Live Production Links
- **Interactive Geospatial Dashboard**: [https://hiten1007.github.io/airsense-iq/](https://hiten1007.github.io/airsense-iq/)
- **FastAPI Production Service**: [https://airsense-iq-le3j.onrender.com/](https://airsense-iq-le3j.onrender.com/)
- **Swagger Documentation**: [https://airsense-iq-le3j.onrender.com/docs](https://airsense-iq-le3j.onrender.com/docs)
- **Container Registry (GHCR)**: `ghcr.io/hiten1007/airsense-iq/aqi-predictor:latest`
