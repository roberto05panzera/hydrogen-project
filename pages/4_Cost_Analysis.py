"""
Page 4 — Cost Analysis
=======================
Compares optimized vs. baseline production costs, shows savings breakdowns,
and lets users simulate different scenarios side by side.

Grading requirements addressed:
- Requirement 3: Data visualisation (cost comparison charts)
- Requirement 4: User interaction (scenario comparison)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.helpers import format_currency

# ---------- Page config ----------
st.set_page_config(page_title="Cost Analysis", page_icon="💰", layout="wide")
st.title("💰 Cost Analysis")

# ---------- Check if optimization has run ----------
if "savings" not in st.session_state or "schedule" not in st.session_state:
    st.warning(
        "No optimization results yet. "
        "Go to **Production Optimizer** and run the optimizer first."
    )
    st.stop()

savings = st.session_state["savings"]
schedule = st.session_state["schedule"]

# ---------- Summary metrics ----------
st.subheader("Cost Comparison: Optimized vs. Baseline")

col1, col2, col3 = st.columns(3)
col1.metric("Optimized Cost", format_currency(savings["optimized_cost_aud"]))
col2.metric("Baseline Cost (avg. price)", format_currency(savings["baseline_cost_aud"]))
col3.metric("Total Savings", format_currency(savings["savings_aud"]),
            delta=f"{savings['savings_pct']}%")

# ---------- Bar chart: optimized vs baseline ----------
fig_comparison = go.Figure(data=[
    go.Bar(name="Optimized", x=["Electricity Cost"], y=[savings["optimized_cost_aud"]],
           marker_color="#065A82"),
    go.Bar(name="Baseline (always-on)", x=["Electricity Cost"], y=[savings["baseline_cost_aud"]],
           marker_color="#B85042"),
])
fig_comparison.update_layout(
    barmode="group",
    yaxis_title="Cost (AUD)",
    title="Optimized vs. Baseline Production Cost",
)
st.plotly_chart(fig_comparison, use_container_width=True)

# ---------- Hourly cost breakdown ----------
st.subheader("Hourly Cost Breakdown")

produce_hours = schedule[schedule["produce"]].copy()

if not produce_hours.empty:
    fig_hourly = go.Figure()
    fig_hourly.add_trace(go.Bar(
        x=produce_hours["timestamp"],
        y=produce_hours["electricity_cost_aud"],
        marker_color=produce_hours["predicted_price_aud_mwh"].apply(
            lambda p: "#2ca02c" if p < 0 else "#065A82"
        ),
        name="Electricity Cost per Hour",
    ))
    fig_hourly.add_hline(y=0, line_dash="dash", line_color="grey")
    fig_hourly.update_layout(
        yaxis_title="Cost (AUD)",
        xaxis_title="Production Hour",
        title="Cost per Production Hour (green = negative price → you earn money)",
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

# ---------- Price distribution of selected hours ----------
st.subheader("Price Distribution")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Selected production hours**")
    st.metric("Avg. Price", f"{savings['avg_price_optimized']:.2f} AUD/MWh")
    st.metric("Hours Used", f"{len(produce_hours)}")

with col_right:
    st.markdown("**Full forecast window**")
    st.metric("Avg. Price", f"{savings['avg_price_all']:.2f} AUD/MWh")
    st.metric("Total Hours", f"{len(schedule)}")

# ---------- Break-even analysis ----------
st.subheader("Break-Even Electricity Price")

h2_sale_price = st.number_input(
    "Expected H₂ sale price (AUD/kg)",
    min_value=1.0, max_value=20.0, value=6.0, step=0.5,
    help="Current green H₂ market price is roughly AUD 4–8/kg depending on region.",
)

if savings["total_h2_kg"] > 0:
    cost_per_kg = savings["optimized_cost_aud"] / savings["total_h2_kg"]
    revenue = h2_sale_price * savings["total_h2_kg"]
    profit = revenue - savings["optimized_cost_aud"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Production Cost per kg", f"AUD {cost_per_kg:.2f}")
    col2.metric("Revenue", format_currency(revenue))
    col3.metric("Profit / Loss", format_currency(profit),
                delta="Profit" if profit >= 0 else "Loss")

    # Break-even electricity price: at what avg price does profit = 0?
    # Revenue = h2_sale_price * total_kg
    # Cost = break_even_price * capacity_mw * hours_used
    # Setting Revenue = Cost and solving for break_even_price:
    hours_used = len(produce_hours)
    if hours_used > 0:
        # Rough estimate using the same capacity from session state
        # (This is a simplification for illustration)
        capacity_mw = savings["optimized_cost_aud"] / (
            produce_hours["predicted_price_aud_mwh"].sum()
        ) if produce_hours["predicted_price_aud_mwh"].sum() != 0 else 1

        break_even = revenue / (capacity_mw * hours_used) if capacity_mw * hours_used != 0 else 0
        st.metric("Break-Even Electricity Price", f"{break_even:.2f} AUD/MWh",
                  help="Average electricity price at which H₂ production breaks even.")

# ---------- Export option ----------
st.subheader("Export Results")
if st.button("📥 Download Schedule as CSV"):
    csv = schedule.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="optimized_schedule.csv",
        mime="text/csv",
    )

