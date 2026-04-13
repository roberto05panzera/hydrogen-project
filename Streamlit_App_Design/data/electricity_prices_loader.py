"""
electricity_prices_loader.py — Loads real AEMO electricity price data.

This module reads TWO data sources and merges them:

  1. Historical AEMO CSVs (PRICE_AND_DEMAND_YYYYMM_REGION.csv)
     - Monthly 5-minute interval data downloaded in bulk
     - Used for ML training and as a fallback when the API is down

  2. Live 7-day prices fetched directly from the OpenElectricity API
     - Fetched on every app load (cached for 1 hour)
     - Provides current market prices for the dashboard

The live data supplements the historical CSVs so that the app always
has near-real-time prices.  If the API call fails, the loader
gracefully falls back to historical data only.

We aggregate everything to hourly averages because:
  - 5-minute data is too noisy for visualisation
  - Our ML model predicts hourly prices
  - Charts load faster with ~8,700 rows/year vs ~105,000

Usage in any page:
    from data.electricity_prices_loader import load_prices, load_live_prices

Data files:
    data/electricity_prices/PRICE_AND_DEMAND_YYYYMM_REGION.csv  (historical)
"""

import os
import glob
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import streamlit as st


# =====================================================================
# CONFIGURATION
# =====================================================================

# Directory where the AEMO CSV files are stored
_PRICES_DIR = os.path.join(os.path.dirname(__file__), "electricity_prices")

# Map our short region names to the AEMO region codes used in filenames
_REGION_FILE_CODES = {
    "NSW": "NSW1",
    "VIC": "VIC1",
    "QLD": "QLD1",
    "SA":  "SA1",
    "TAS": "TAS1",
}

# Map NEM sub-region codes (from the API) back to our short names
_NEM_REGION_MAP = {
    "NSW1": "NSW",
    "VIC1": "VIC",
    "QLD1": "QLD",
    "SA1":  "SA",
    "TAS1": "TAS",
}

# OpenElectricity API config
_OE_API_KEY = "oe_DYiKF1FeoE9VzmEPNuzUCV"
_OE_BASE_URL = "https://api.openelectricity.org.au/v4/market/network"


# =====================================================================
# LIVE API FETCH — self-contained, no external script dependency
# =====================================================================

@st.cache_data(ttl=3600, show_spinner="Fetching live prices from AEMO...")
def _fetch_live_prices_from_api() -> pd.DataFrame:
    """
    Fetch the last 7 days of 5-minute NEM prices directly from the
    OpenElectricity API and return hourly averages for ALL regions.

    Cached for 1 hour (ttl=3600) so we don't hit the API on every
    Streamlit rerun.

    Returns DataFrame with columns:
        timestamp      (datetime, hourly)
        price_aud_mwh  (float, hourly average)
        region         (str, e.g. "NSW", "TAS")

    Returns empty DataFrame if the API call fails.
    """
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=7)

    try:
        resp = requests.get(
            f"{_OE_BASE_URL}/NEM",
            headers={"Authorization": f"Bearer {_OE_API_KEY}"},
            params={
                "interval": "5m",
                "metrics": "price",
                "primary_grouping": "network_region",
                "with_clerk": "true",
                "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end":   now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as e:
        # Store the error so the UI can show it
        st.session_state["_api_error"] = str(e)
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    # Parse the nested JSON response
    rows = []
    try:
        api_data = resp.json().get("data", [])
        for top_item in api_data:
            for result in top_item.get("results", []):
                nem_code = result.get("columns", {}).get("region")
                region = _NEM_REGION_MAP.get(nem_code)
                if region is None:
                    continue
                for ts_str, price in result.get("data", []):
                    if price is None or ts_str is None:
                        continue
                    rows.append({
                        "timestamp": ts_str,
                        "price": float(price),
                        "region": region,
                    })
    except Exception as e:
        st.session_state["_api_error"] = f"Parse error: {e}"
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    if not rows:
        st.session_state["_api_error"] = "API returned no price data"
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    # Convert to DataFrame and aggregate to hourly
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)   # strip tz for consistency
    df["hour"] = df["timestamp"].dt.floor("h")

    hourly = df.groupby(["hour", "region"]).agg(
        price_aud_mwh=("price", "mean"),
    ).reset_index()
    hourly.rename(columns={"hour": "timestamp"}, inplace=True)
    hourly["price_aud_mwh"] = hourly["price_aud_mwh"].round(2)

    # Clear any previous error
    st.session_state.pop("_api_error", None)

    return hourly


def load_live_prices(region_abbr: str = "NSW") -> pd.DataFrame:
    """
    Get live 7-day prices for ONE region from the API.

    This is the public function called by Market Overview and other
    pages that want current prices.

    Returns DataFrame with columns:
        timestamp      (datetime, hourly)
        price_aud_mwh  (float)

    Returns empty DataFrame if the API call fails.
    """
    all_live = _fetch_live_prices_from_api()

    if all_live.empty:
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh"])

    region_data = all_live[all_live["region"] == region_abbr].copy()
    return region_data[["timestamp", "price_aud_mwh"]].reset_index(drop=True)


# =====================================================================
# HISTORICAL CSV LOADER
# =====================================================================

def _load_historical_prices(region_abbr: str = "NSW") -> pd.DataFrame:
    """
    Load and concatenate all AEMO price CSVs for a given NEM region,
    then aggregate from 5-minute intervals to hourly averages.

    Parameters:
        region_abbr: short region name, e.g. "NSW", "VIC"

    Returns DataFrame with columns:
        timestamp       (datetime, hourly)
        price_aud_mwh   (float, hourly average)
        demand_gw       (float, hourly average in GW)
    """
    file_code = _REGION_FILE_CODES.get(region_abbr, "NSW1")
    pattern = os.path.join(_PRICES_DIR, f"PRICE_AND_DEMAND_*_{file_code}.csv")
    csv_files = sorted(glob.glob(pattern))

    if not csv_files:
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "demand_gw"])

    frames = [pd.read_csv(f) for f in csv_files]
    raw = pd.concat(frames, ignore_index=True)

    raw["timestamp"] = pd.to_datetime(raw["SETTLEMENTDATE"])
    raw["hour"] = raw["timestamp"].dt.floor("h")

    hourly = raw.groupby("hour").agg(
        price_aud_mwh=("RRP", "mean"),
        demand_mw=("TOTALDEMAND", "mean"),
    ).reset_index()
    hourly.rename(columns={"hour": "timestamp"}, inplace=True)
    hourly["demand_gw"] = (hourly["demand_mw"] / 1000).round(2)
    hourly.drop(columns=["demand_mw"], inplace=True)
    hourly["price_aud_mwh"] = hourly["price_aud_mwh"].round(2)

    return hourly


# =====================================================================
# COMBINED LOADER — historical + live
# =====================================================================

def load_prices(region_abbr: str = "NSW") -> pd.DataFrame:
    """
    Load ALL available price data: historical CSVs + live API.

    Live API data takes priority for overlapping timestamps.

    Parameters:
        region_abbr: short region name, e.g. "NSW", "VIC", "QLD", "SA", "TAS"

    Returns DataFrame with columns:
        timestamp       (datetime, hourly)
        price_aud_mwh   (float, hourly average RRP in AUD/MWh)
        demand_gw       (float, hourly average total demand in GW — NaN for live data)
    """
    # Load historical from CSVs
    hist = _load_historical_prices(region_abbr)

    # Fetch live 7-day data from the API
    live = load_live_prices(region_abbr)

    if not live.empty:
        live["demand_gw"] = float("nan")

        # Remove historical rows that overlap with live data
        if not hist.empty:
            hist = hist[~hist["timestamp"].isin(live["timestamp"])]

        combined = pd.concat([hist, live], ignore_index=True)
    else:
        combined = hist

    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined
