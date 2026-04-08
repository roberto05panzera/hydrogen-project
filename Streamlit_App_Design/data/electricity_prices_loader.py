"""
electricity_prices_loader.py — Loads real AEMO electricity price data.

This module reads the PRICE_AND_DEMAND CSV files downloaded from AEMO
(Australian Energy Market Operator) and provides clean, hourly-aggregated
DataFrames that the front-end pages can use directly.

The raw CSVs contain 5-minute interval data with columns:
    REGION, SETTLEMENTDATE, TOTALDEMAND, RRP, PERIODTYPE

We aggregate to hourly averages because:
  - 5-minute data is too noisy for visualisation
  - Our ML model predicts hourly prices
  - Charts load faster with ~8,700 rows/year vs ~105,000

Usage in any page:
    from data.electricity_prices_loader import load_prices

Data files live in:  data/electricity_prices/PRICE_AND_DEMAND_YYYYMM_REGION.csv
"""

import os
import glob
import pandas as pd


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


def load_prices(region_abbr: str = "NSW") -> pd.DataFrame:
    """
    Load and concatenate all AEMO price CSVs for a given NEM region,
    then aggregate from 5-minute intervals to hourly averages.

    Parameters:
        region_abbr: short region name, e.g. "NSW", "VIC", "QLD", "SA", "TAS"

    Returns DataFrame with columns:
        timestamp       (datetime, hourly)
        price_aud_mwh   (float, hourly average RRP in AUD/MWh)
        demand_gw       (float, hourly average total demand in GW)
    """
    # Get the AEMO file code for this region (e.g. "NSW" → "NSW1")
    file_code = _REGION_FILE_CODES.get(region_abbr, "NSW1")

    # Find all CSV files matching this region using a glob pattern
    # e.g. PRICE_AND_DEMAND_202501_NSW1.csv, PRICE_AND_DEMAND_202502_NSW1.csv, ...
    pattern = os.path.join(_PRICES_DIR, f"PRICE_AND_DEMAND_*_{file_code}.csv")
    csv_files = sorted(glob.glob(pattern))

    # If no files found, return an empty DataFrame
    if not csv_files:
        return pd.DataFrame(columns=["timestamp", "price_aud_mwh", "demand_gw"])

    # Read and concatenate all monthly CSVs into one big DataFrame
    frames = []
    for f in csv_files:
        df = pd.read_csv(f)
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)

    # Parse the settlement date column into proper datetime objects
    raw["timestamp"] = pd.to_datetime(raw["SETTLEMENTDATE"])

    # Floor each timestamp to the hour (e.g. 14:35 → 14:00)
    # This groups all 5-minute intervals within each hour together
    raw["hour"] = raw["timestamp"].dt.floor("h")

    # Aggregate: average price and demand per hour
    hourly = raw.groupby("hour").agg(
        price_aud_mwh=("RRP", "mean"),             # average price
        demand_mw=("TOTALDEMAND", "mean"),          # average demand in MW
    ).reset_index()

    # Rename the hour column to timestamp for consistency
    hourly.rename(columns={"hour": "timestamp"}, inplace=True)

    # Convert demand from MW to GW (divide by 1000) for cleaner display
    hourly["demand_gw"] = (hourly["demand_mw"] / 1000).round(2)
    hourly.drop(columns=["demand_mw"], inplace=True)

    # Round price to 2 decimal places
    hourly["price_aud_mwh"] = hourly["price_aud_mwh"].round(2)

    # Sort chronologically
    hourly = hourly.sort_values("timestamp").reset_index(drop=True)

    return hourly
