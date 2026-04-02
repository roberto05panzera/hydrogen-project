"""
Page 3 — Production Optimizer
===============================
The core of the app: users enter their electrolyzer parameters and hydrogen
target, and the optimizer selects the cheapest production hours from the
price forecast.

Grading requirements addressed:
- Requirement 1: Clear business problem (cost-optimized H2 production)
- Requirement 4: User interaction (sliders, inputs, file upload)
- Requirement 3: Data visualisation (production schedule chart)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.optimizer import optimize_schedule, calculate_savings
from utils.helpers import (
    AUSTRALIAN_REGIONS,
    DEFAULT_CAPACITY_MW,
    DEFAULT_EFFICIENCY_KWH_PER_KG,
    DEFAULT_TARGET_H2_KG,
    format_currency,
    format_price_per_kg,
)

# ---------- Page config ----------
st.set_page_config(page_title="Production Optimizer", page_icon="🔧", layout="wide")
st.title("🔧 Production Optimizer")

# ---------- Check if forecast data is available ----------
if "price_forecast" not in st.session_state:
    st.warning(
        "No price forecast available yet. "
        "Please go to **Price Forecast** and train the model first."
    )
    st.stop()

# ---------- Sidebar: user parameters ----------
st.sidebar.header("Electrolyzer Parameters")

capacity_mw = st.sidebar.number_input(
    "Electrolyzer Capacity (MW)",
    min_value=0.5, max_value=100.0, value=float(DEFAULT_CAPACITY_MW), step=0.5,
)

efficiency = st.sidebar.number_input(
    "Efficiency (kWh per kg H₂)",
    min_value=30.0, max_value=80.0, value=DEFAULT_EFFICIENCY_KWH_PER_KG, step=0.5,
    help="Typical PEM electrolyzer: 50–55 kWh/kg. Alkaline: 45–50 kWh/kg.",
)

target_kg = st.sidebar.number_input(
    "Target H₂ Production (kg)",
    min_value=10.0, max_value=50000.0, value=float(DEFAULT_TARGET_H2_KG), step=50.0,
)

st.sidebar.markdown("---")

# ---------- Optional: upload custom price data ----------
st.sidebar.subheader("📁 Or Upload Custom Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload price CSV or Excel",
    type=["csv", "xlsx"],
    help="Must contain columns 'timestamp' and 'price_aud_mwh'.",
)

# ---------- Determine which price data to use ----------
if uploaded_file is not None:
    # Read uploaded file
    if uploaded_file.name.endswith(".csv"):
        custom_df = pd.read_csv(uploaded_file, parse_dates=["timestamp"])
    else:
        custom_df = pd.read_excel(uploaded_file, parse_dates=["timestamp"])

    # Validate required columns
    if "timestamp" in custom_df.columns and "price_aud_mwh" in custom_df.columns:
        price_forecast = custom_df.rename(columns={"price_aud_mwh": "predicted_price_aud_mwh"})
        st.success(f"Using uploaded data: {len(price_forecast)} rows loaded.")
    else:
        st.error("Uploaded file must have 'timestamp' and 'price_aud_mwh' columns.")
        st.stop()
else:
    price_forecast = st.session_state["price_forecast"]

# ---------- Run optimizer ----------
if st.button("⚡ Optimize Production Schedule", type="primary"):
    schedule = optimize_schedule(
        price_forecast=price_forecast,
        electrolyzer_capacity_mw=capacity_mw,
        efficiency_kwh_per_kg=efficiency,
        target_h2_kg=target_kg,
    )

    savings = calculate_savings(schedule, capacity_mw)

    # Store for cost analysis page
    st.session_state["schedule"] = schedule
    st.session_state["savings"] = savings

    # --- Results summary ---
    st.subheader("Optimization Results")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total H₂ Produced", f"{savings['total_h2_kg']:,.1f} kg")
    col2.metric("Optimized Cost", format_currency(savings["optimized_cost_aud"]))
    col3.metric("Baseline Cost", format_currency(savings["baseline_cost_aud"]))
    col4.metric("Savings", f"{savings['savings_pct']}%",
                delta=format_currency(savings["savings_aud"]))

    st.metric("Cost per kg H₂",
              format_price_per_kg(savings["optimized_cost_aud"], savings["total_h2_kg"]))

    # --- Schedule chart: prices with production hours highlighted ---
    st.subheader("Optimal Production Schedule")

    fig = go.Figure()

    # All hours (grey line)
    fig.add_trace(go.Scatter(
        x=schedule["timestamp"],
        y=schedule["predicted_price_aud_mwh"],
        mode="lines", name="Predicted Price",
        line=dict(color="lightgrey"),
    ))

    # Production hours (colored markers)
    produce_df = schedule[schedule["produce"]]
    fig.add_trace(go.Bar(
        x=produce_df["timestamp"],
        y=produce_df["predicted_price_aud_mwh"],
        name="Production Hours",
        marker_color=np.where(produce_df["predicted_price_aud_mwh"] < 0, "#2ca02c", "#065A82"),
        opacity=0.7,
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.update_layout(
        yaxis_title="Price (AUD/MWh)",
        xaxis_title="Time",
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Data table (expandable) ---
    with st.expander("View full schedule data"):
        display_df = schedule[["timestamp", "predicted_price_aud_mwh", "produce",
                               "h2_produced_kg", "electricity_cost_aud"]].copy()
        display_df.columns = ["Time", "Price (AUD/MWh)", "Produce?", "H₂ (kg)", "Cost (AUD)"]
        st.dataframe(display_df, use_container_width=True)

else:
    st.info("Adjust parameters in the sidebar and click **Optimize Production Schedule**.")
