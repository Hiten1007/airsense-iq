import pytest
import pandas as pd
import numpy as np
from src.features import (
    add_cyclical_time_features,
    add_meteorological_features,
    add_lag_and_rolling_features,
    build_feature_pipeline,
    split_train_test_time_series
)


@pytest.fixture
def sample_raw_dataframe():
    dates = pd.date_range("2024-01-01 00:00:00", periods=72, freq="h")
    df = pd.DataFrame({
        "time": dates,
        "pm2_5": np.random.uniform(20.0, 150.0, size=72),
        "pm10": np.random.uniform(40.0, 200.0, size=72),
        "nitrogen_dioxide": np.random.uniform(10.0, 60.0, size=72),
        "temperature_2m": np.random.uniform(15.0, 35.0, size=72),
        "relative_humidity_2m": np.random.uniform(30.0, 80.0, size=72),
        "wind_speed_10m": np.random.uniform(1.0, 15.0, size=72),
        "wind_direction_10m": np.random.uniform(0.0, 360.0, size=72),
    })
    return df


def test_add_cyclical_time_features(sample_raw_dataframe):
    df = add_cyclical_time_features(sample_raw_dataframe)
    for col in ["hour_sin", "hour_cos", "month_sin", "month_cos", "dayofweek_sin", "dayofweek_cos", "is_weekend"]:
        assert col in df.columns
        assert df[col].notna().all()

    # Sine and cosine bounds [-1.0, 1.0]
    assert (df["hour_sin"] >= -1.0 - 1e-6).all() and (df["hour_sin"] <= 1.0 + 1e-6).all()
    assert (df["hour_cos"] >= -1.0 - 1e-6).all() and (df["hour_cos"] <= 1.0 + 1e-6).all()


def test_add_meteorological_features(sample_raw_dataframe):
    df = add_meteorological_features(sample_raw_dataframe)
    assert "wind_u" in df.columns
    assert "wind_v" in df.columns
    assert "ventilation_index" in df.columns
    assert df["wind_u"].notna().all()


def test_add_lag_and_rolling_features(sample_raw_dataframe):
    df = add_lag_and_rolling_features(
        sample_raw_dataframe,
        target_col="pm2_5",
        lags=[1, 2, 24],
        rolling_windows=[6, 12]
    )
    assert "pm2_5_lag_1" in df.columns
    assert "pm2_5_lag_2" in df.columns
    assert "pm2_5_lag_24" in df.columns
    assert "pm2_5_rolling_mean_6" in df.columns
    assert "pm2_5_rolling_mean_12" in df.columns

    # Verify no lookahead: pm2_5_lag_1 at row 1 must match pm2_5 at row 0
    assert df["pm2_5_lag_1"].iloc[1] == df["pm2_5"].iloc[0]


def test_build_feature_pipeline(sample_raw_dataframe):
    processed = build_feature_pipeline(sample_raw_dataframe, drop_na=True)
    assert not processed.empty
    assert processed.isna().sum().sum() == 0


def test_split_train_test_time_series(sample_raw_dataframe):
    train_df, test_df = split_train_test_time_series(sample_raw_dataframe, test_days=1)
    assert not train_df.empty
    assert not test_df.empty
    # Ensure temporal boundary: max train time < min test time
    assert train_df["time"].max() < test_df["time"].min()
