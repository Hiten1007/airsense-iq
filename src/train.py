import os
import sys
import json
import logging
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from src.data_loader import fetch_and_merge_historical_dataset, load_config
from src.features import build_feature_pipeline, split_train_test_time_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def prepare_training_data(
    raw_df: pd.DataFrame,
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame, list, str]:
    """
    Run feature engineering and split into time-series train and test sets.
    """
    data_cfg = config["data"]
    target_col = data_cfg.get("target_column", "pm2_5")
    test_days = data_cfg.get("test_days", 30)
    feat_cfg = config.get("features", {})

    logger.info("Applying feature engineering pipeline...")
    featured_df = build_feature_pipeline(
        raw_df,
        target_col=target_col,
        lags=feat_cfg.get("lags"),
        rolling_windows=feat_cfg.get("rolling_windows"),
        drop_na=True
    )

    # Save processed features
    processed_path = data_cfg.get("processed_data_path", "data/processed/featured_data.csv")
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    featured_df.to_csv(processed_path, index=False)
    logger.info(f"Processed feature matrix saved to {processed_path} (Shape: {featured_df.shape})")

    # Time-series split
    train_df, test_df = split_train_test_time_series(featured_df, test_days=test_days)
    logger.info(f"Train samples: {len(train_df)}, Test samples: {len(test_df)} (Holdout: last {test_days} days)")

    # Exclude metadata and target columns from feature list
    feature_cols = [c for c in train_df.columns if c not in ["time", target_col]]
    return train_df, test_df, feature_cols, target_col


def train_lightgbm_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_params: Dict[str, Any]
) -> LGBMRegressor:
    """
    Train a LightGBM regressor on engineered time-series features.
    """
    logger.info("Training LightGBM Regressor...")
    model = LGBMRegressor(**model_params)
    model.fit(X_train, y_train)
    return model


def train_baseline_model(
    X_train: pd.DataFrame,
    y_train: pd.Series
) -> RandomForestRegressor:
    """
    Train a simple Random Forest baseline for sanity benchmarking.
    """
    logger.info("Training Baseline Model (Random Forest)...")
    baseline = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1)
    baseline.fit(X_train, y_train)
    return baseline


def run_training_pipeline(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Execute end-to-end training: Ingestion -> Features -> Train Candidate -> Save Artifacts.
    """
    config = load_config(config_path)
    raw_path = config["data"].get("raw_data_path", "data/raw/aqi_data.csv")

    if os.path.exists(raw_path):
        logger.info(f"Loading cached raw data from {raw_path}...")
        raw_df = pd.read_csv(raw_path)
        raw_df["time"] = pd.to_datetime(raw_df["time"])
    else:
        logger.info("Raw data not found locally. Ingesting from Open-Meteo...")
        raw_df = fetch_and_merge_historical_dataset(config_path)

    train_df, test_df, feature_cols, target_col = prepare_training_data(raw_df, config)

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    model_cfg = config.get("model", {})
    candidate_model = train_lightgbm_model(X_train, y_train, model_cfg.get("params", {}))

    # Evaluate on Train Set
    y_train_pred = candidate_model.predict(X_train)
    train_r2 = r2_score(y_train, y_train_pred)
    train_rmse = float(np.sqrt(mean_squared_error(y_train, y_train_pred)))
    logger.info(f"Train Metrics -> R2: {train_r2:.4f}, RMSE: {train_rmse:.2f}")

    # Evaluate on Holdout Test Set
    y_test_pred = candidate_model.predict(X_test)
    test_r2 = r2_score(y_test, y_test_pred)
    test_rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    logger.info(f"Holdout Test Metrics -> R2: {test_r2:.4f}, RMSE: {test_rmse:.2f}, MAE: {test_mae:.2f}")

    # Persist Candidate Model and Feature Schema
    model_dir = model_cfg.get("model_dir", "models")
    os.makedirs(model_dir, exist_ok=True)
    candidate_path = model_cfg.get("candidate_model_path", "models/candidate_model.joblib")
    joblib.dump(candidate_model, candidate_path)
    logger.info(f"Candidate model saved to {candidate_path}")

    # Save feature names list for inference validation
    feature_meta_path = os.path.join(model_dir, "feature_names.json")
    with open(feature_meta_path, "w") as f:
        json.dump(feature_cols, f, indent=2)

    # Save candidate metrics for gating
    candidate_metrics = {
        "train_r2": float(train_r2),
        "train_rmse": float(train_rmse),
        "test_r2": float(test_r2),
        "test_rmse": float(test_rmse),
        "test_mae": float(test_mae),
        "feature_count": len(feature_cols),
        "train_samples": len(train_df),
        "test_samples": len(test_df)
    }

    metrics_path = model_cfg.get("metrics_path", "models/metrics.json")
    with open(metrics_path, "w") as f:
        json.dump({"candidate": candidate_metrics}, f, indent=2)
    logger.info(f"Metrics saved to {metrics_path}")

    # Save test set for gate comparison
    test_path = "data/processed/test_holdout.csv"
    test_df.to_csv(test_path, index=False)

    return candidate_metrics


if __name__ == "__main__":
    metrics = run_training_pipeline()
    print("Training Pipeline Execution Completed:", metrics)
