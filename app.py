#placeholder <- Entry point (landing page / overview)
"""
Hydrogen Production Optimizer — Main Entry Point
=================================================
This is the landing page of the Streamlit app.
Run it with:  streamlit run app.py

The pages/ folder contains the individual pages that appear in the sidebar.
The utils/ folder contains shared logic (API calls, ML model, optimizer).
"""

import streamlit as st

# ---------- Page config (must be the first Streamlit command) ----------
st.set_page_config(
    page_title="H2 Production Optimizer",
    page_icon="⚡",
    layout="wide",
)

# ---------- Landing page content ----------
st.title("⚡ Hydrogen Production Optimizer")
st.subheader("Utilizing Negative Electricity Prices for Green Hydrogen Production")

st.markdown(
    """
    Welcome to the **H2 Production Optimizer** — a platform that helps hydrogen
    producers reduce electricity costs by predicting price movements and
    scheduling production during the cheapest hours.

    **Use the sidebar** to navigate between pages:

    1. **Market Overview** — Live electricity prices and weather data for Australia
    2. **Price Forecast** — ML-based price predictions with confidence bands
    3. **Production Optimizer** — Enter your parameters and get an optimal schedule
    4. **Cost Analysis** — Compare strategies and estimate savings
    """
)

# ---------- Quick status indicators (placeholder) ----------
col1, col2, col3 = st.columns(3)

with col1:
    # TODO: Replace with real-time data from utils/api.py
    st.metric(label="Current Avg. Price (AUD/MWh)", value="42.10", delta="-3.5")

with col2:
    st.metric(label="Negative-Price Hours (last 24h)", value="4", delta="2")

with col3:
    st.metric(label="Potential Savings", value="18%", delta="5%")

st.info("ℹ️ These values are placeholders. Connect the AEMO API to show live data.")

# ---------- Sidebar branding ----------
st.sidebar.markdown("### Group 4.04 — *Not Found*")
st.sidebar.markdown("Fundamentals of Computer Science · HS 2026")
