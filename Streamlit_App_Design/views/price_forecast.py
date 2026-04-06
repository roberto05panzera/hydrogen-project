"""
price_forecast.py — Price Forecast page.

This page lets the user:
  1. Pick a forecast model (Linear Regression / Random Forest / XGBoost)
  2. See a chart of historical prices + the model's forecast with a
     confidence interval (shaded band)
  3. View model accuracy metrics (RMSE, MAE, R²) as KPI cards
  4. View feature importance as a horizontal bar chart

Data comes from data/sample_data.py for now.  When the ML team's
real model is ready, just swap the import source — the page code
stays the same because the data format is identical.
"""

import streamlit as st
import plotly.graph_objects as go              # Plotly for interactive charts
from style import COLORS
from components import metric_card, dashboard_card, stats_row

# Import placeholder data functions.
# get_forecast()           → dict with timestamps, actual, predicted,
#                            lower/upper bounds, and metrics
# get_feature_importance() → DataFrame with feature names and scores
from data.sample_data import get_forecast, get_feature_importance


def render():
    """Draw the Price Forecast page.  Called by app.py."""

    # ==============================================================
    # STEP 1: MODEL SELECTOR + KPI METRICS ROW
    # ==============================================================
    # A horizontal radio lets the user pick which ML model to display.
    # The forecast data and metrics update instantly when they switch.
    # This counts as a user interaction for grading.

    # ── Model selector ──
    # st.radio with horizontal=True shows the options as clickable tabs.
    # We map the display labels to the internal keys that get_forecast()
    # expects (e.g. "Linear Regression" → "linear_regression").
    model_display = st.radio(
        label="Forecast Model",
        options=["Linear Regression", "Random Forest", "XGBoost"],
        index=0,                                   # default: first option
        horizontal=True,                            # tabs side-by-side
        key="forecast_model_selector",
    )

    # Convert the display name to the key format used by sample_data.py
    # "Linear Regression" → "linear_regression"
    model_key = model_display.lower().replace(" ", "_")

    # ── Fetch forecast data for the selected model ──
    # This returns a dict with: timestamps, actual, predicted,
    # lower_bound, upper_bound, hist_hours, model_name, metrics
    forecast = get_forecast(model_name=model_key, horizon_hours=48)

    # Extract the metrics sub-dict for easy access
    metrics = forecast["metrics"]

    # ── KPI row: three metric cards showing model performance ──
    # RMSE = Root Mean Squared Error (lower is better)
    # MAE  = Mean Absolute Error (lower is better)
    # R²   = Coefficient of determination (closer to 1.0 is better)
    kpi1, kpi2, kpi3 = st.columns(3)

    with kpi1:
        # RMSE — colour green if below 10, orange otherwise
        rmse_color = COLORS["green"] if metrics["rmse"] < 10 else COLORS["orange"]
        metric_card(
            label="RMSE",
            value=f"{metrics['rmse']:.2f}",
            subtitle="AUD/MWh — lower is better",
            color=rmse_color,
        )

    with kpi2:
        # MAE — colour green if below 8, orange otherwise
        mae_color = COLORS["green"] if metrics["mae"] < 8 else COLORS["orange"]
        metric_card(
            label="MAE",
            value=f"{metrics['mae']:.2f}",
            subtitle="AUD/MWh — lower is better",
            color=mae_color,
        )

    with kpi3:
        # R² — colour green if above 0.7, orange otherwise
        r2_color = COLORS["green"] if metrics["r2"] > 0.7 else COLORS["orange"]
        metric_card(
            label="R² SCORE",
            value=f"{metrics['r2']:.3f}",
            subtitle="1.0 = perfect fit",
            color=r2_color,
        )

    # Small spacing below the KPI row
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

    # ==============================================================
    # STEP 2: FORECAST CHART CARD
    # ==============================================================
    # The main chart on this page.  It shows:
    #   - Historical actual prices (solid white line)
    #   - Model's predicted prices (dashed accent-blue line)
    #   - Confidence interval (semi-transparent shaded band)
    #   - A vertical dashed line marking "now" (where history ends
    #     and the forecast begins)
    #
    # The chart is wrapped in dashboard_card() for the dark border
    # and title bar.  The modal (Step 3) will be wired up later.

    def draw_forecast_chart():
        """
        Draw the forecast chart inside a dashboard_card.

        Three visual layers:
          1. Confidence band — shaded area between lower and upper bound
          2. Actual prices   — solid line (only for historical period)
          3. Predicted prices — dashed line (full range: history + forecast)
        Plus a vertical "now" line separating history from forecast.
        """
        # Unpack the forecast data
        ts          = forecast["timestamps"]       # list of datetime objects
        actual      = forecast["actual"]           # list of floats
        predicted   = forecast["predicted"]        # list of floats
        lower       = forecast["lower_bound"]      # list of floats
        upper       = forecast["upper_bound"]      # list of floats
        hist_hours  = forecast["hist_hours"]       # int: index where forecast starts

        # Create an empty Plotly figure
        fig = go.Figure()

        # ── Layer 1: Confidence interval (shaded band) ──
        # We draw the upper bound as one trace and the lower bound as
        # another, then use fill="tonexty" on the lower trace to shade
        # the area between them.  This is the same technique we used
        # for Bollinger Bands on the Market Overview page.

        # Upper bound (invisible line — just defines the top of the band)
        fig.add_trace(go.Scatter(
            x=ts,
            y=upper,
            mode="lines",
            line=dict(width=0),                    # invisible line
            showlegend=False,
            hoverinfo="skip",                      # don't show on hover
            name="Upper CI",
        ))

        # Lower bound + fill up to the upper bound
        fig.add_trace(go.Scatter(
            x=ts,
            y=lower,
            mode="lines",
            line=dict(width=0),                    # invisible line
            fill="tonexty",                        # shade between this and previous trace
            fillcolor="rgba(0,102,255,0.10)",      # semi-transparent accent blue
            showlegend=False,
            hoverinfo="skip",
            name="Lower CI",
        ))

        # ── Layer 2: Actual prices (historical only) ──
        # We only plot actual values up to hist_hours because we don't
        # have "actual" future prices — that's what we're forecasting.
        fig.add_trace(go.Scatter(
            x=ts[:hist_hours],
            y=actual[:hist_hours],
            mode="lines",
            name="Actual",
            line=dict(
                color=COLORS["text_primary"],      # white
                width=1.5,
            ),
        ))

        # ── Layer 3: Predicted prices (full range) ──
        # The predicted line runs across both historical and forecast
        # periods.  In the historical part you can visually compare it
        # against the actual line to see how accurate the model is.
        fig.add_trace(go.Scatter(
            x=ts,
            y=predicted,
            mode="lines",
            name="Predicted",
            line=dict(
                color=COLORS["accent"],            # electric blue
                width=2,
                dash="dash",                       # dashed line
            ),
        ))

        # ── "Now" divider line ──
        # A vertical dashed line marking where history ends and the
        # forecast begins.  This is the most important visual cue —
        # everything to the right is a prediction, not real data.
        #
        # NOTE: We draw this manually with go.Scatter instead of
        # fig.add_vline() because add_vline's annotation parameter
        # crashes on newer Plotly + Python 3.14 (it tries to call
        # sum() on datetime objects).  A manual trace is more robust.
        now_ts = ts[hist_hours]                    # timestamp at the boundary

        # Find the y-axis range so the vertical line spans the full chart
        all_vals = actual[:hist_hours] + predicted
        y_min = min(all_vals) - 5
        y_max = max(all_vals) + 5

        fig.add_trace(go.Scatter(
            x=[now_ts, now_ts],                    # same x = vertical line
            y=[y_min, y_max],                      # spans full y range
            mode="lines",
            line=dict(color=COLORS["yellow"], width=1, dash="dash"),
            showlegend=False,
            hoverinfo="skip",
            name="Now",
        ))

        # Add a "Now" text label at the top of the divider line
        fig.add_annotation(
            x=now_ts,
            y=y_max,
            text="Now",
            showarrow=False,
            font=dict(color=COLORS["yellow"], size=10),
            yshift=10,                             # nudge label above chart
        )

        # ── Chart styling (dark theme) ──
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",         # transparent
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["text_muted"], size=11),
            margin=dict(l=50, r=20, t=30, b=40),
            height=360,

            # X-axis
            xaxis=dict(
                showgrid=False,
                linecolor=COLORS["border"],
                tickfont=dict(color=COLORS["text_muted"], size=10),
            ),

            # Y-axis
            yaxis=dict(
                title="AUD/MWh",
                title_font=dict(color=COLORS["text_muted"], size=10),
                gridcolor=COLORS["border_light"],
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=COLORS["border"],
                zerolinewidth=0.5,
                tickfont=dict(color=COLORS["text_muted"], size=10),
            ),

            # Legend at the top so it doesn't overlap the chart
            legend=dict(
                orientation="h",                   # horizontal legend
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=10),
            ),

            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True, key="forecast_chart")

    # Wrap the chart in a dashboard card with a title bar.
    # modal_content_func will be added in Step 3.
    dashboard_card(
        title=f"Price Forecast — {model_display} ({metrics['horizon_hours']}h horizon)",
        content_func=draw_forecast_chart,
    )
