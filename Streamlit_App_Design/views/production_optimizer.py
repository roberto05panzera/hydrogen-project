"""
production_optimizer.py — Production Optimizer page.

This is the core "hydrogen" page.  It lets the user:
  1. Set electrolyser parameters (capacity, break-even price, window)
  2. See an optimal production schedule — green = produce, red = hold
  3. View cost summary KPIs (total cost, H₂ output, cost per kg)
  4. Compare "Optimised" vs "Naive 24/7" production strategies

The optimizer logic is simple: for each hour, if the forecasted
electricity price is below the user's break-even threshold → produce.
Otherwise → hold.  The front-end visualises the result.

Data comes from data/sample_data.py.  The functions already handle
the optimisation math — we just pass in the user's slider values.
"""

import streamlit as st
import plotly.graph_objects as go              # Plotly for interactive charts
from style import COLORS
from components import metric_card, dashboard_card, stats_row

# Import placeholder data functions.
# get_electrolyser_defaults() → dict with default slider values
# get_optimised_schedule()    → DataFrame: timestamp, price, produce, h2_kg, cost_aud
# get_optimizer_summary()     → dict with optimised vs naive comparison
from data.sample_data import (
    get_electrolyser_defaults,
    get_optimised_schedule,
    get_optimizer_summary,
)


def render():
    """Draw the Production Optimizer page.  Called by app.py."""

    # ==============================================================
    # STEP 1: INPUT CONTROLS
    # ==============================================================
    # Three interactive controls that let the user tweak the
    # electrolyser settings.  Every change re-runs the schedule
    # calculation and updates the entire page.
    #
    # Each control = a user interaction for grading.

    # Load default values for the sliders / inputs.
    # This keeps the defaults in one place (sample_data.py) so the
    # ML team can adjust them later without touching front-end code.
    defaults = get_electrolyser_defaults()

    # ── Layout: three columns for the controls ──
    ctrl1, ctrl2, ctrl3 = st.columns(3)

    with ctrl1:
        # Electrolyser capacity slider (in MW).
        # Bigger capacity = more H₂ per hour, but higher electricity cost.
        capacity_mw = st.slider(
            label="Electrolyser Capacity (MW)",
            min_value=defaults["capacity_range"][0],    # 1 MW
            max_value=defaults["capacity_range"][1],    # 50 MW
            value=defaults["capacity_mw"],               # default: 10 MW
            step=1,
            key="optimizer_capacity",
            help="Size of the electrolyser in megawatts. "
                 "Larger = more hydrogen per hour.",
        )

    with ctrl2:
        # Break-even electricity price (AUD/MWh).
        # If the spot price is BELOW this → produce (it's profitable).
        # If the spot price is ABOVE this → hold (too expensive).
        breakeven = st.number_input(
            label="Break-even Price (AUD/MWh)",
            min_value=defaults["breakeven_range"][0],   # 10.0
            max_value=defaults["breakeven_range"][1],   # 120.0
            value=defaults["breakeven_price"],           # default: 45.0
            step=5.0,
            key="optimizer_breakeven",
            help="Maximum electricity price at which hydrogen "
                 "production is still profitable.",
        )

    with ctrl3:
        # Production window — how many hours to plan ahead.
        # "48 h" = 2 days, "7 days" = full week
        window_label = st.radio(
            label="Planning Window",
            options=["48 h", "7 days"],
            index=1,                                     # default: 7 days
            horizontal=True,
            key="optimizer_window",
            help="How far ahead to plan the production schedule.",
        )

        # Convert label to hours: "48 h" → 48, "7 days" → 168
        horizon = 48 if window_label == "48 h" else 168

    # Small spacing between controls and content
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

    # ── Fetch optimised schedule and summary with user's settings ──
    # These functions use the slider values to compute the schedule.
    schedule = get_optimised_schedule(
        breakeven=breakeven,
        capacity_mw=capacity_mw,
        horizon_hours=horizon,
    )
    summary = get_optimizer_summary(
        breakeven=breakeven,
        capacity_mw=capacity_mw,
    )

    # Shortcuts to the optimised and naive sub-dicts
    opt = summary["optimised"]
    naive = summary["naive"]
    savings = summary["savings"]

    # ==============================================================
    # STEP 2: KPI SUMMARY ROW
    # ==============================================================
    # Four metric cards showing the key outcomes of the optimised
    # schedule.  All values update dynamically when the user moves
    # the sliders above.

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        # Production hours — how many of the total hours the
        # electrolyser is actually running
        metric_card(
            label="PRODUCTION HOURS",
            value=f"{opt['production_hours']}h",
            subtitle=f"of {naive['production_hours']}h total",
            color=COLORS["accent"],
        )

    with kpi2:
        # Total H₂ output in kilograms
        metric_card(
            label="H₂ OUTPUT",
            value=f"{opt['total_h2_kg']:,.0f} kg",
            subtitle=f"vs {naive['total_h2_kg']:,.0f} kg naive",
            color=COLORS["green"],
        )

    with kpi3:
        # Total electricity cost
        # Colour green if negative (we're being PAID to consume),
        # otherwise use the default text colour
        cost_color = COLORS["green"] if opt["total_cost_aud"] < 0 else COLORS["text_primary"]
        metric_card(
            label="TOTAL COST",
            value=f"${opt['total_cost_aud']:,.0f}",
            subtitle="AUD electricity cost",
            color=cost_color,
        )

    with kpi4:
        # Cost per kg of H₂ — the bottom-line efficiency metric
        metric_card(
            label="COST PER KG",
            value=f"${opt['cost_per_kg']:.2f}",
            subtitle=f"vs ${naive['cost_per_kg']:.2f} naive",
            color=COLORS["green"] if opt["cost_per_kg"] < naive["cost_per_kg"] else COLORS["red"],
        )

    # Small spacing below KPI row
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
