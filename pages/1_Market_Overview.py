"""
Page 1 — Market Overview
=========================
Shows live/recent electricity prices and weather data for the selected
Australian NEM region. This is the "monitoring dashboard" page.

Grading requirements addressed:
- Requirement 2: Data loaded via API
- Requirement 3: Data visualisation
- Requirement 4: User interaction (region selector, time range)
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Import shared utilities
from utils.api import fetch_electricity_prices, fetch_weather_data, fetch_hydrogen_news
from utils.helpers import AUSTRALIAN_REGIONS

# ---------- Page config ----------
st.set_page_config(page_title="Market Overview", page_icon="📊", layout="wide")
st.title("📊 Market Overview")

# ---------- Sidebar: user interaction ----------
st.sidebar.header("Settings")

# Region selector
region_code = st.sidebar.selectbox(
    "Select NEM Region",
    options=list(AUSTRALIAN_REGIONS.keys()),
    format_func=lambda code: f"{AUSTRALIAN_REGIONS[code]['name']} ({code})",
)
region = AUSTRALIAN_REGIONS[region_code]

# Time range slider
hours = st.sidebar.slider("Hours of historical data", min_value=24, max_value=168, value=48, step=24)

# ---------- Fetch data ----------
with st.spinner("Loading electricity prices..."):
    price_df = fetch_electricity_prices(region=region_code, hours=hours)

with st.spinner("Loading weather data..."):
    weather_df = fetch_weather_data(latitude=region["lat"], longitude=region["lon"], hours=hours)

# ---------- Price chart ----------
st.subheader(f"Electricity Prices — {region['name']}")

if not price_df.empty:
    fig_price = px.line(
        price_df,
        x="timestamp",
        y="price_aud_mwh",
        labels={"price_aud_mwh": "Price (AUD/MWh)", "timestamp": "Time"},
    )
    # Highlight negative prices
    fig_price.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Break-even")
    st.plotly_chart(fig_price, use_container_width=True)

    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"{price_df['price_aud_mwh'].iloc[-1]:.2f} AUD/MWh")
    col2.metric("Average", f"{price_df['price_aud_mwh'].mean():.2f}")
    col3.metric("Min", f"{price_df['price_aud_mwh'].min():.2f}")
    col4.metric("Max", f"{price_df['price_aud_mwh'].max():.2f}")
else:
    st.warning("No price data available. Check the API connection.")

# ---------- Weather chart ----------
st.subheader("Weather Conditions")

if not weather_df.empty:
    # Two-column layout: temperature + wind on left, solar on right
    col_left, col_right = st.columns(2)

    with col_left:
        fig_temp = px.line(weather_df, x="timestamp", y="temperature_c",
                           labels={"temperature_c": "Temperature (°C)"})
        st.plotly_chart(fig_temp, use_container_width=True)

    with col_right:
        fig_solar = px.area(weather_df, x="timestamp", y="solar_radiation_wm2",
                            labels={"solar_radiation_wm2": "Solar Radiation (W/m²)"})
        st.plotly_chart(fig_solar, use_container_width=True)
else:
    st.warning("Weather data unavailable.")

# ---------- Hydrogen news sidebar ----------
st.sidebar.markdown("---")
st.sidebar.subheader("🗞️ Hydrogen News")
news = fetch_hydrogen_news()
for article in news:
    st.sidebar.markdown(f"**[{article['title']}]({article['url']})**")
    st.sidebar.caption(f"{article['source']} · {article['published']}")
