"""
electricity_prices_loader.py — Loads real AEMO electricity price data.

CODE VERSION: 2026-04-13-v4

This module reads TWO data sources and merges them:

  1. Historical AEMO CSVs (PRICE_AND_DEMAND_YYYYMM_REGION.csv)
     - Monthly 5-minute interval data downloaded in bulk
     - Used for ML training and as a fallback when the API is down

  2. Live 7-day prices fetched directly from the OpenElectricity API
     - Fetched on every app load (cached for 10 min on success only)
     - Provides current market prices for the dashboard

Usage in any page:
    from data.electricity_prices_loader import load_prices, load_live_prices
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

_PRICES_DIR = os.path.join(os.path.dirname(__file__), "electricity_prices")

_REGION_FILE_CODES = {
    "NSW": "NSW1",
    "VIC": "VIC1",
    "QLD": "QLD1",
    "SA":  "SA1",
    "TAS": "TAS1",
}

_NEM_REGION_MAP = {
    "NSW1": "NSW",
    "VIC1": "VIC",
    "QLD1": "QLD",
    "SA1":  "SA",
    "TAS1": "TAS",
}

_OE_API_KEY = "oe_DYiKF1FeoE9VzmEPNuzUCV"
_OE_BASE_URL = "https://api.openelectricity.org.au/v4/market/network"


# =====================================================================
# LIVE API FETCH — self-contained, no external script dependency
# =====================================================================

def _fetch_live_prices_from_api() -> pd.DataFrame:
    """
    Fetch the last 7 days of 5-minute NEM prices directly from the
    OpenElectricity API and return hourly averages for ALL regions.

    NOT cached with @st.cache_data — we handle caching manually so
    that failures are retried on every page load, while successes
    are cached for 10 minutes.
    """
    # ── Manual cache: only cache successful results ──
    cache_key = "_live_prices_cache"
    cache_ts_key = "_live_prices_cache_ts"
    cached = st.session_state.get(cache_key)
    cached_ts = st.session_state.get(cache_ts_key)

    if cached is not None and cached_ts is not None:
        age_seconds = (datetime.now(timezone.utc) - cached_ts).total_seconds()
        if age_seconds < 600 and not cached.empty:
            # Return cached SUCCESS result (< 10 min old)
            return cached
        # If cached result was empty (failure), don't use it — retry immediately

    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=7)

    # ── Try primary parameter format (camelCase — per official SDK) ──
    param_sets = [
        {
            "interval": "5m",
            "metrics": "price",
            "primaryGrouping": "network_region",
            "dateStart": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dateEnd":   now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        # Fallback: snake_case variant (older API versions)
        {
            "interval": "5m",
            "metrics": "price",
            "primary_grouping": "network_region",
            "date_start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_end":   now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    ]

    resp = None
    last_error = None

    for params in param_sets:
        try:
            resp = requests.get(
                f"{_OE_BASE_URL}/NEM",
                headers={"Authorization": f"Bearer {_OE_API_KEY}"},
                params=params,
                timeout=30,
            )

            # Store raw status for diagnostics
            st.session_state["_api_status_code"] = resp.status_code
            st.session_state["_api_response_preview"] = resp.text[:500]
            st.session_state["_api_params_used"] = str(params)

            resp.raise_for_status()
            break  # success — stop trying further param sets

        except Exception as e:
            last_error = e
            resp = None
            continue

    if resp is None:
        st.session_state["_api_error"] = str(last_error)
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    # Parse the nested JSON response — handle multiple response formats
    rows = []
    try:
        raw_json = resp.json()

        # Format A: { "data": [ { "results": [ { "columns": {...}, "data": [...] } ] } ] }
        api_data = raw_json.get("data", [])

        if isinstance(api_data, list) and len(api_data) > 0:
            for top_item in api_data:
                # Handle both nested and flat result structures
                results = top_item.get("results", [top_item])
                for result in results:
                    nem_code = result.get("columns", {}).get("region")
                    if nem_code is None:
                        nem_code = result.get("columns", {}).get("network_region")
                    region = _NEM_REGION_MAP.get(nem_code)
                    if region is None:
                        continue
                    data_points = result.get("data", [])
                    for point in data_points:
                        if isinstance(point, (list, tuple)) and len(point) >= 2:
                            ts_str, price = point[0], point[1]
                        elif isinstance(point, dict):
                            ts_str = point.get("date") or point.get("timestamp")
                            price = point.get("price") or point.get("value")
                        else:
                            continue
                        if price is None or ts_str is None:
                            continue
                        rows.append({
                            "timestamp": ts_str,
                            "price": float(price),
                            "region": region,
                        })

        # Store diagnostic info about parsing
        st.session_state["_api_rows_parsed"] = len(rows)
        st.session_state["_api_json_keys"] = str(list(raw_json.keys())[:10])

    except Exception as e:
        st.session_state["_api_error"] = f"Parse error: {e}"
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    if not rows:
        st.session_state["_api_error"] = "API returned 200 but no price data in response"
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "region"])

    # Convert to DataFrame and aggregate to hourly
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df["hour"] = df["timestamp"].dt.floor("h")

    hourly = df.groupby(["hour", "region"]).agg(
        price_aud_mwh=("price", "mean"),
    ).reset_index()
    hourly.rename(columns={"hour": "timestamp"}, inplace=True)
    hourly["price_aud_mwh"] = hourly["price_aud_mwh"].round(2)

    # Clear error and cache success
    st.session_state.pop("_api_error", None)
    st.session_state[cache_key] = hourly
    st.session_state[cache_ts_key] = datetime.now(timezone.utc)

    return hourly


def load_live_prices(region_abbr: str = "NSW") -> pd.DataFrame:
    """
    Get live 7-day prices for ONE region from the API.
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
    """
    hist = _load_historical_prices(region_abbr)
    live = load_live_prices(region_abbr)

    if not live.empty:
        live["demand_gw"] = float("nan")
        if not hist.empty:
            hist = hist[~hist["timestamp"].isin(live["timestamp"])]
        combined = pd.concat([hist, live], ignore_index=True)
    else:
        combined = hist

    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined
