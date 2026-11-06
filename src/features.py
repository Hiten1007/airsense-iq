import numpy as np
import pandas as pd
from typing import List, Optional, Tuple


def add_cyclical_time_features(df: pd.DataFrame, time_col: str = "time") -> pd.DataFrame:
    """
    Extract temporal attributes and encode cyclical sine/cosine representations.
    """
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])

    hour = df[time_col].dt.hour
    dayofweek = df[time_col].dt.dayofweek
    month = df[time_col].dt.month
    dayofyear = df[time_col].dt.dayofyear

    # Cyclical encodings
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    df["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * month / 12.0)
    df["dayofweek_sin"] = np.sin(2 * np.pi * dayofweek / 7.0)
    df["dayofweek_cos"] = np.cos(2 * np.pi * dayofweek / 7.0)

    df["is_weekend"] = (dayofweek >= 5).astype(int)
    return df


def add_meteorological_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute physical wind vector components (U and V) and ventilation proxy.
    """
    df = df.copy()
    if "wind_speed_10m" in df.columns and "wind_direction_10m" in df.columns:
        rad = np.radians(df["wind_direction_10m"])
        # Wind U (east-west) and V (north-south) components
        df["wind_u"] = -df["wind_speed_10m"] * np.sin(rad)
        df["wind_v"] = -df["wind_speed_10m"] * np.cos(rad)

    if "temperature_2m" in df.columns and "wind_speed_10m" in df.columns:
        # Ventilation index approximation (temperature * wind)
        df["ventilation_index"] = (df["temperature_2m"] + 273.15) * df["wind_speed_10m"]

    return df


def add_lag_and_rolling_features(
    df: pd.DataFrame,
    target_col: str = "pm2_5",
    lags: Optional[List[int]] = None,
    rolling_windows: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Create time-series lag and rolling statistics without data leakage.
    Lags are applied to target and key pollutants.
    Rolling statistics are computed on lagged values (shift 1).
    """
    df = df.copy()
    if lags is None:
        lags = [1, 2, 3, 6, 12, 24]
    if rolling_windows is None:
        rolling_windows = [6, 12, 24]

    # Target lags
    for lag in lags:
        df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)

    # Secondary pollutant lags if present
    for col in ["pm10", "nitrogen_dioxide", "ozone"]:
        if col in df.columns:
            for lag in [1, 2, 24]:
                df[f"{col}_lag_{lag}"] = df[col].shift(lag)

    # Rolling statistics based on shift(1) to avoid lookahead leakage
    target_shifted = df[target_col].shift(1)
    for window in rolling_windows:
        df[f"{target_col}_rolling_mean_{window}"] = target_shifted.rolling(window=window, min_periods=1).mean()
        df[f"{target_col}_rolling_std_{window}"] = target_shifted.rolling(window=window, min_periods=1).std().fillna(0)

    return df


def build_feature_pipeline(
    df: pd.DataFrame,
    target_col: str = "pm2_5",
    lags: Optional[List[int]] = None,
    rolling_windows: Optional[List[int]] = None,
    drop_na: bool = True
) -> pd.DataFrame:
    """
    End-to-end feature pipeline execution.
    """
    # 1. Forward-fill and backward-fill raw missing values
    processed_df = df.ffill().bfill()

    # 2. Add cyclical time features
    processed_df = add_cyclical_time_features(processed_df, time_col="time")

    # 3. Add meteorological physics features
    processed_df = add_meteorological_features(processed_df)

    # 4. Add lag and rolling features
    processed_df = add_lag_and_rolling_features(
        processed_df,
        target_col=target_col,
        lags=lags,
        rolling_windows=rolling_windows
    )

    # 5. Drop initial rows with NaN from lags if requested
    if drop_na:
        processed_df = processed_df.dropna().reset_index(drop=True)

    return processed_df


def split_train_test_time_series(
    df: pd.DataFrame,
    test_days: int = 30,
    time_col: str = "time"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Perform a clean temporal split: hold out the last `test_days` for evaluation.
    Guarantees no future information leaks into training.
    """
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    cutoff_time = df_sorted[time_col].max() - pd.Timedelta(days=test_days)

    train_df = df_sorted[df_sorted[time_col] <= cutoff_time].copy()
    test_df = df_sorted[df_sorted[time_col] > cutoff_time].copy()

    return train_df, test_df
