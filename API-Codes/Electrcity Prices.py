import schedule
import time
from datetime import datetime, timezone
import requests
import pytz
import csv
import os
import json

# ============================================================
# API CONFIG
# ============================================================

API_KEY = "oe_DYiKF1FeoE9VzmEPNuzUCV"
BASE_URL = "https://api.openelectricity.org.au/v4/market/network/NEM"

REGIONS = ["AU-SA", "AU-VIC", "AU-NSW", "AU-QLD", "AU-TAS"]

REGION_TIMEZONES = {
    "AU-SA":  "Australia/Adelaide",
    "AU-VIC": "Australia/Melbourne",
    "AU-NSW": "Australia/Sydney",
    "AU-QLD": "Australia/Brisbane",
    "AU-TAS": "Australia/Hobart"
}

NETWORK_REGION_TO_AU = {
    "SA1":  "AU-SA",
    "VIC1": "AU-VIC",
    "NSW1": "AU-NSW",
    "QLD1": "AU-QLD",
    "TAS1": "AU-TAS"
}

CSV_FILE = "electricity_price_data.csv"
RAW_DEBUG_FILE = "last_api_response.json"

# ============================================================
# DATA STORAGE
# ============================================================

class ElectricityPriceAU:
    def __init__(self):
        self.storage = {}

au_price = ElectricityPriceAU()

# ============================================================
# CSV
# ============================================================

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["region_code", "date", "price"])

def append_to_csv(region, region_dt, price):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            region,
            region_dt.strftime("%Y-%m-%d %H:%M:%S"),
            price
        ])

# ============================================================
# HELPERS
# ============================================================

def parse_dt(value):
    """Parse an ISO 8601 timestamp string into a UTC datetime."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except Exception:
        return None

def get_latest_non_null(data_pairs):
    """
    data_pairs is a list of [timestamp_str, price_or_null].
    Returns the last entry where price is not None, or None if none found.
    """
    for ts_str, price in reversed(data_pairs):
        if price is not None:
            return ts_str, price
    return None, None

# ============================================================
# MAIN
# ============================================================

def retrieve_latest_data():
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        params={
            "interval": "5m",
            "metrics": "price",
            "primary_grouping": "network_region",
            "with_clerk": "true"
        },
        timeout=30
    )

    if response.status_code != 200:
        print(f"✗ Fehler: {response.status_code} | {response.text}")
        return

    api_response = response.json()

    with open(RAW_DEBUG_FILE, "w", encoding="utf-8") as f:
        json.dump(api_response, f, indent=2, ensure_ascii=False)

    # The API returns a single top-level data item containing all regions
    # Structure: data[0].results = list of { columns: {region: "NSW1"}, data: [[ts, price], ...] }
    data = api_response.get("data", [])
    if not isinstance(data, list) or not data:
        print("✗ Keine Daten in response['data']")
        return

    wrote_anything = False

    for top_item in data:
        results = top_item.get("results", [])
        if not isinstance(results, list):
            continue

        for result in results:
            # Extract region from columns dict
            columns = result.get("columns", {})
            raw_region = columns.get("region")
            region = NETWORK_REGION_TO_AU.get(raw_region)

            if region not in REGIONS:
                continue

            data_pairs = result.get("data", [])
            if not isinstance(data_pairs, list) or not data_pairs:
                continue

            # Get the most recent data point with a non-null price
            ts_str, price = get_latest_non_null(data_pairs)

            if ts_str is None or price is None:
                print(f"✗ {region} | Kein gültiger Preis gefunden")
                continue

            api_dt = parse_dt(ts_str)
            if api_dt is None:
                print(f"✗ {region} | Ungültiger Timestamp: {ts_str}")
                continue

            tz = pytz.timezone(REGION_TIMEZONES[region])
            region_dt = api_dt.astimezone(tz)

            if region not in au_price.storage:
                au_price.storage[region] = {}

            au_price.storage[region][region_dt] = price
            append_to_csv(region, region_dt, price)
            wrote_anything = True

            print(f"✓ {region} | {region_dt.strftime('%d.%m.%Y %H:%M')} → {price} $/MWh")

    if not wrote_anything:
        print("✗ Response erhalten, aber keine parsebaren Datensätze gefunden.")
        print(f"→ Checke {RAW_DEBUG_FILE}")

# ============================================================
# START
# ============================================================

init_csv()

print("▶ Aktuelle Daten wurden abgerufen:")
retrieve_latest_data()

schedule.every(5).minutes.do(retrieve_latest_data)

print("▶ Scheduler gestartet: Daten werden alle 5 Minuten aktualisiert")

while True:
    schedule.run_pending()
    time.sleep(30)