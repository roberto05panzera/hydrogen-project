"""
carbon_intensity_loader.py — Load carbon intensity data from Electricity Maps CSVs.

Previously this function lived in sample_data.py.  Now it has its own
module so that price_forecast.py doesn't depend on sample_data at all.

The raw CSVs are in data/carbon_intensity/ and were collected via the
Electricity Maps API (carbon_intensity_API_live_data.py).

Usage:
    from data.carbon_intensity_loader import get_carbon_intensity

    df = get_carbon_intensity(region_abbr="NSW", days=30)
    # → DataFrame with columns: datetime, carbon_intensity
"""

import os
import pandas as pd


# =====================================================================
# REGION MAPPING
# =====================================================================
# Map short region abbreviations (used in the sidebar) to the
# Electricity Maps API region codes (used in the CSV filenames).

_CARBON_REGION_MAP = {
    "NSW": "AU-NSW",
    "VIC": "AU-VIC",
    "QLD": "AU-QLD",
    "SA":  "AU-SA",
    "TAS": "AU-TAS",
}

# Map API region codes to the actual CSV file paths.
# Each file contains hourly carbon intensity data for one region.
_CARBON_DIR = os.path.join(os.path.dirname(__file__), "carbon_intensity")

_CARBON_CSV_FILES = {
    "AU-NSW": os.path.join(_CARBON_DIR, "carbon_nsw.csv"),
    "AU-VIC": os.path.join(_CARBON_DIR, "carbon_vic.csv"),
    "AU-QLD": os.path.join(_CARBON_DIR, "carbon_qld.csv"),
    "AU-SA":  os.path.join(_CARBON_DIR, "carbon_sa.csv"),
    "AU-TAS": os.path.join(_CARBON_DIR, "carbon_tas.csv"),
}


# =====================================================================
# LOADER FUNCTION
# =====================================================================

def get_carbon_intensity(region_abbr: str = "NSW", days: int = 30) -> pd.DataFrame:
    """
    Load carbon intensity data for a given NEM region.

    Reads from the real CSV files collected via the Electricity Maps API.
    Returns the most recent `days` worth of hourly data.

    Parameters:
        region_abbr: short region name, e.g. "NSW", "VIC", "QLD", "SA", "TAS"
        days:        how many days of history to return (default 30)

    Returns DataFrame with columns:
        datetime          (pd.Timestamp)  — hourly timestamp
        carbon_intensity  (float)         — gCO₂eq/kWh
    """
    # Convert our region abbreviation to the API region code
    region_code = _CARBON_REGION_MAP.get(region_abbr, "AU-NSW")

    # Read the CSV for this region
    csv_path = _CARBON_CSV_FILES.get(region_code)
    try:
        df = pd.read_csv(csv_path)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
    except Exception:
        # If the file doesn't exist or can't be read, return empty DataFrame
        return pd.DataFrame(columns=["datetime", "carbon_intensity"])

    # Return only the last N days of data
    if len(df) > 0:
        cutoff = df["datetime"].max() - pd.Timedelta(days=days)
        df = df[df["datetime"] >= cutoff]

    return df.reset_index(drop=True)
