import os
import pytest
import pandas as pd
from src.predict import categorize_pm2_5, load_champion_model, predict_from_dataframe
from src.evaluate import evaluate_model


def test_categorize_pm2_5():
    assert categorize_pm2_5(15.0) == "Good"
    assert categorize_pm2_5(45.0) == "Satisfactory"
    assert categorize_pm2_5(75.0) == "Moderate"
    assert categorize_pm2_5(110.0) == "Poor"
    assert categorize_pm2_5(200.0) == "Very Poor"
    assert categorize_pm2_5(350.0) == "Severe"


def test_champion_model_loading():
    if os.path.exists("models/champion/model.joblib"):
        model, feature_names, config = load_champion_model()
        assert model is not None
        assert len(feature_names) > 0
        assert "city" in config


def test_evaluate_model_metrics():
    test_data_path = "data/processed/test_holdout.csv"
    champion_path = "models/champion/model.joblib"

    if os.path.exists(test_data_path) and os.path.exists(champion_path):
        test_df = pd.read_csv(test_data_path)
        metrics = evaluate_model(champion_path, test_df)

        assert "r2" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["r2"] > 0.5  # Basic sanity floor
        assert metrics["rmse"] < 100.0
