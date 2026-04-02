"""
API Module — Data Retrieval
============================
All external API calls live here. Every other file imports from this module
rather than making its own HTTP requests. This keeps API logic in one place
and makes it easy to swap data sources later.

Key principle: each function returns a pandas DataFrame with clearly named
columns so that pages and other utils can rely on a stable interface.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# AEMO Electricity Prices (Australia)
# ---------------------------------------------------------------------------
# The Australian Energy Market Operator publishes 5-minute dispatch prices.
# Docs: https://aemo.com.au/energy-systems/electricity/
#       national-electricity-market-nem/data-nem/
#
# TODO: Replace the placeholder below with a real AEMO API call or CSV download.
# ---------------------------------------------------------------------------

def fetch_electricity_prices(region: str = "NSW1", hours: int = 48) -> pd.DataFrame:
    """
    Fetch recent electricity prices for an Australian NEM region.

    Parameters
    ----------
    region : str
        NEM region code, e.g. "NSW1", "VIC1", "QLD1", "SA1", "TAS1".
    hours : int
        How many hours of historical data to retrieve.

    Returns
    -------
    pd.DataFrame
        Columns: ["timestamp", "price_aud_mwh"]
        - timestamp : datetime  (UTC)
        - price_aud_mwh : float (AUD per MWh)
    """
    # --- PLACEHOLDER: generates fake price data for development ---
    # Remove this block and replace with real API call when ready.
    import numpy as np

    np.random.seed(42)
    now = datetime.utcnow()
    timestamps = [now - timedelta(hours=hours) + timedelta(hours=i) for i in range(hours)]
    # Simulate volatile prices with occasional negative dips
    base = 50 + 20 * np.sin(np.linspace(0, 4 * np.pi, hours))
    noise = np.random.normal(0, 15, hours)
    prices = base + noise

    df = pd.DataFrame({"timestamp": timestamps, "price_aud_mwh": prices})
    return df


# ---------------------------------------------------------------------------
# Weather Data (Open-Meteo — free, no API key needed)
# ---------------------------------------------------------------------------
# Docs: https://open-meteo.com/en/docs
# ---------------------------------------------------------------------------

def fetch_weather_data(latitude: float = -33.87, longitude: float = 151.21,
                       hours: int = 48) -> pd.DataFrame:
    """
    Fetch hourly weather forecast from Open-Meteo (no API key required).

    Parameters
    ----------
    latitude, longitude : float
        Coordinates (default: Sydney).
    hours : int
        Forecast horizon in hours.

    Returns
    -------
    pd.DataFrame
        Columns: ["timestamp", "temperature_c", "wind_speed_kmh",
                   "solar_radiation_wm2"]
    """
    # --- REAL API CALL (Open-Meteo is free) ---
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,wind_speed_10m,direct_radiation",
        "forecast_days": max(1, hours // 24),
        "timezone": "UTC",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["hourly"]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(data["time"]),
            "temperature_c": data["temperature_2m"],
            "wind_speed_kmh": data["wind_speed_10m"],
            "solar_radiation_wm2": data["direct_radiation"],
        })
        return df.head(hours)

    except Exception as e:
        # If the API call fails, return an empty DataFrame so the app
        # doesn't crash — the page can show a warning instead.
        print(f"Weather API error: {e}")
        return pd.DataFrame(columns=[
            "timestamp", "temperature_c", "wind_speed_kmh", "solar_radiation_wm2"
        ])


# ---------------------------------------------------------------------------
# Hydrogen News (placeholder)
# ---------------------------------------------------------------------------
# TODO: Integrate a news API (e.g. NewsAPI.org, GNews) with query "hydrogen"
# ---------------------------------------------------------------------------

def fetch_hydrogen_news(max_articles: int = 5) -> list[dict]:
    """
    Fetch recent hydrogen-related news articles.

    Returns
    -------
    list of dict
        Each dict has keys: "title", "url", "source", "published"
    """
    # --- PLACEHOLDER ---
    return [
        {
            "title": "Australia announces new green hydrogen export hub",
            "url": "https://example.com/article1",
            "source": "Energy News",
            "published": "2026-03-28",
        },
        {
            "title": "Negative prices hit record in South Australia",
            "url": "https://example.com/article2",
            "source": "AEMO Insights",
            "published": "2026-03-25",
        },
    ]
