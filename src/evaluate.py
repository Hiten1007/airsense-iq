import os
import sys
import logging
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def evaluate_model(
    model_path: str,
    test_df: pd.DataFrame,
    target_col: str = "pm2_5"
) -> Dict[str, float]:
    """
    Evaluate a saved model against a test dataset and calculate performance metrics.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}")

    model = joblib.load(model_path)
    feature_cols = [c for c in test_df.columns if c not in ["time", target_col]]

    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    mean_bias = float((y_pred - y_test).mean())

    metrics = {
        "r2": float(r2),
        "rmse": float(rmse),
        "mae": float(mae),
        "mean_bias": mean_bias,
        "sample_count": len(test_df)
    }

    logger.info(
        f"Evaluation for {os.path.basename(model_path)} -> "
        f"R2: {r2:.4f}, RMSE: {rmse:.2f}, MAE: {mae:.2f}, Bias: {mean_bias:.2f}"
    )
    return metrics


if __name__ == "__main__":
    config = load_config()
    candidate_path = config["model"]["candidate_model_path"]
    test_data_path = "data/processed/test_holdout.csv"

    if os.path.exists(test_data_path) and os.path.exists(candidate_path):
        test_data = pd.read_csv(test_data_path)
        metrics = evaluate_model(candidate_path, test_data)
        print("Evaluation Results:", metrics)
    else:
        print("Model or test holdout data not found. Run train.py first.")
