"""
ML Model Module — Price Prediction
====================================
Contains everything related to the machine learning pipeline:
feature engineering, training, evaluation, and prediction.

The approach follows a standard supervised learning workflow:
1. Build features from historical prices + weather + time variables
2. Train a regression model (Linear Regression as baseline)
3. Evaluate on a held-out test set (MSE)
4. Predict future prices for the next 24–72 hours

Other files use this module like so:
    from utils.model import train_model, predict_prices
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def build_features(price_df: pd.DataFrame, weather_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Create the feature matrix from raw price and weather data.

    Features created:
    - hour_of_day   (0–23)  — captures daily price patterns
    - day_of_week   (0–6)   — captures weekday vs. weekend effects
    - price_lag_1h          — price one hour ago
    - price_lag_24h         — price 24 hours ago (same hour yesterday)
    - temperature_c         — from weather data (if available)
    - wind_speed_kmh        — from weather data (if available)
    - solar_radiation_wm2   — from weather data (if available)

    Parameters
    ----------
    price_df : pd.DataFrame
        Must have columns ["timestamp", "price_aud_mwh"].
    weather_df : pd.DataFrame, optional
        Must have columns ["timestamp", "temperature_c", "wind_speed_kmh",
        "solar_radiation_wm2"].

    Returns
    -------
    pd.DataFrame
        Feature matrix with target column "price_aud_mwh".
    """
    df = price_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Time-based features
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    # Lagged price features
    df["price_lag_1h"] = df["price_aud_mwh"].shift(1)
    df["price_lag_24h"] = df["price_aud_mwh"].shift(24)

    # Merge weather data if available
    if weather_df is not None and not weather_df.empty:
        weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"])
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            weather_df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
        )

    # Drop rows with NaN from lagging
    df = df.dropna().reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

# These are the columns the model expects as input (X).
# Keep this list in sync with build_features().
FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "price_lag_1h",
    "price_lag_24h",
]

# If weather data is merged in, these get added automatically.
WEATHER_COLUMNS = ["temperature_c", "wind_speed_kmh", "solar_radiation_wm2"]


def train_model(features_df: pd.DataFrame, test_size: float = 0.3):
    """
    Train a Linear Regression model on the prepared feature DataFrame.

    Parameters
    ----------
    features_df : pd.DataFrame
        Output of build_features(). Must contain FEATURE_COLUMNS + "price_aud_mwh".
    test_size : float
        Fraction of data to hold out for testing (default 30%).

    Returns
    -------
    model : LinearRegression
        Trained sklearn model.
    mse : float
        Mean Squared Error on the test set.
    X_test, y_test : pd.DataFrame, pd.Series
        Test data (useful for plotting actual vs. predicted).
    """
    # Determine which feature columns are actually present
    available_features = [c for c in FEATURE_COLUMNS + WEATHER_COLUMNS
                          if c in features_df.columns]

    X = features_df[available_features]
    y = features_df["price_aud_mwh"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False  # time series: don't shuffle
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)

    return model, mse, X_test, y_test


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_prices(model, future_features: pd.DataFrame) -> pd.DataFrame:
    """
    Use a trained model to predict future electricity prices.

    Parameters
    ----------
    model : LinearRegression (or any sklearn-compatible model)
        A trained model from train_model().
    future_features : pd.DataFrame
        Must contain the same feature columns the model was trained on.
        Typically built by hand or from forecast weather data.

    Returns
    -------
    pd.DataFrame
        Columns: ["timestamp", "predicted_price_aud_mwh"]
    """
    # Determine which columns the model expects
    available_features = [c for c in FEATURE_COLUMNS + WEATHER_COLUMNS
                          if c in future_features.columns]

    predictions = model.predict(future_features[available_features])

    result = future_features[["timestamp"]].copy() if "timestamp" in future_features.columns \
        else pd.DataFrame({"timestamp": range(len(predictions))})
    result["predicted_price_aud_mwh"] = predictions

    return result
