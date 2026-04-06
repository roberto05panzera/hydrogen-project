"""
market_overview.py — Market Overview page (landing page / dashboard).

This is the first page the user sees.  It shows:
  - KPI cards (current price, 24h change, 7-day avg, grid demand)
  - A main price chart with click-to-expand indicator modal
  - A price heatmap, regional comparison, and news/alerts cards

Data comes from data/sample_data.py.  When the real APIs are
connected, only the import source changes — the page code stays
the same.
"""

import streamlit as st
import plotly.graph_objects as go          # Plotly for interactive charts
from style import COLORS
from components import metric_card, dashboard_card

# Import our placeholder data.
# sys.path trick: sample_data.py sits inside data/, which is a
# subfolder.  The __init__.py we created makes it importable.
from data.sample_data import get_market_kpis, get_spot_prices_7d


def region_abbr() -> str:
    """
    Get the short region name (e.g. "NSW") from the sidebar selection.
    The sidebar stores the full name like "New South Wales (NSW)" in
    st.session_state["region"].  This extracts just the abbreviation.
    """
    full = st.session_state.get("region", "New South Wales (NSW)")
    return full.split("(")[-1].replace(")", "").strip()


def render():
    """Draw the Market Overview page.  Called by app.py."""

    # ==============================================================
    # STEP 1: KPI ROW — four metric cards across the top
    # ==============================================================
    # Fetch the current KPI values from our data source.
    # This returns a dict with keys: current_price, avg_24h, avg_7d,
    # grid_demand.  Each has: value, unit, delta, delta_pct.
    kpis = get_market_kpis()

    # Create 4 equal-width columns, one for each KPI card.
    # st.columns(4) returns a list of 4 column objects.
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    # Column 1: Current Spot Price
    # We colour it green because negative prices are good for
    # hydrogen production (cheap electricity = produce now).
    with kpi_col1:
        price = kpis["current_price"]
        metric_card(
            label="SPOT PRICE",
            value=f"${price['value']:.2f}",           # format: $-12.40
            subtitle=price["unit"],                     # "AUD/MWh"
            color=COLORS["green"] if price["value"] < 0 else COLORS["red"],
            delta=f"{price['delta_pct']}%",            # "-134.2%"
        )

    # Column 2: 24-Hour Average
    with kpi_col2:
        avg24 = kpis["avg_24h"]
        metric_card(
            label="24H AVG",
            value=f"${avg24['value']:.2f}",
            subtitle=avg24["unit"],
            color=COLORS["text_primary"],               # neutral white
            delta=f"{avg24['delta_pct']}%",
            delta_color=COLORS["green"] if avg24["delta"] < 0 else COLORS["red"],
        )

    # Column 3: 7-Day Average
    with kpi_col3:
        avg7d = kpis["avg_7d"]
        metric_card(
            label="7-DAY AVG",
            value=f"${avg7d['value']:.2f}",
            subtitle=avg7d["unit"],
            color=COLORS["text_primary"],
            delta=f"+{avg7d['delta_pct']}%" if avg7d["delta"] > 0 else f"{avg7d['delta_pct']}%",
            delta_color=COLORS["red"] if avg7d["delta"] > 0 else COLORS["green"],
        )

    # Column 4: Grid Demand
    with kpi_col4:
        demand = kpis["grid_demand"]
        metric_card(
            label="GRID DEMAND",
            value=f"{demand['value']} GW",
            subtitle=f"{demand['delta_pct']}% vs yesterday",
            color=COLORS["cyan"],
        )

    # Add some spacing below the KPI row before the next section
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

    # ==============================================================
    # STEP 2: MAIN PRICE CHART CARD
    # ==============================================================
    # This is the central chart on the Market Overview page.
    # It shows the last 7 days of spot electricity prices as a
    # Plotly line chart, styled to match our dark finance theme.
    #
    # We wrap it in dashboard_card() so it gets the dark border,
    # title bar, and an "Expand" button.  The expand button will
    # open the indicator modal (Step 3).

    # ── Fetch the price data ──
    # get_spot_prices_7d() returns a DataFrame with columns:
    #   timestamp (datetime), price_aud_mwh (float)
    prices_df = get_spot_prices_7d()

    def draw_price_chart():
        """
        Draw the spot price line chart using Plotly.

        We define this as a function (not inline code) because
        dashboard_card() expects a function it can call to draw
        the card's content.
        """
        # Create an empty Plotly figure
        fig = go.Figure()

        # Add the spot price line
        # go.Scatter draws a line (or scatter plot).
        # mode="lines" means just the line, no dots.
        fig.add_trace(go.Scatter(
            x=prices_df["timestamp"],         # x-axis: time
            y=prices_df["price_aud_mwh"],     # y-axis: price
            mode="lines",                      # just the line, no markers
            name="Spot Price",                 # label for the legend
            line=dict(
                color=COLORS["accent"],        # electric blue
                width=2,                        # line thickness in pixels
            ),
            # "hovertemplate" controls what appears when you hover
            # over a data point.  %{y:.2f} means the y-value with
            # 2 decimal places.  <extra></extra> hides the trace name.
            hovertemplate="$%{y:.2f} AUD/MWh<extra></extra>",
        ))

        # ── Add a break-even reference line ──
        # This horizontal dashed line shows the hydrogen production
        # threshold.  When price is below this line = good to produce.
        breakeven = 45.0
        fig.add_hline(
            y=breakeven,
            line_dash="dash",                  # dashed line style
            line_color=COLORS["yellow"],
            line_width=1,
            annotation_text="Break-even $45",
            annotation_position="top right",
            annotation_font_color=COLORS["yellow"],
            annotation_font_size=10,
        )

        # ── Style the chart to match our dark theme ──
        # update_layout() controls everything about the chart's
        # appearance: background, axes, fonts, margins, etc.
        fig.update_layout(
            # Transparent backgrounds so the card's dark bg shows through
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",

            # Font settings
            font=dict(color=COLORS["text_secondary"], size=11),

            # Remove margins so the chart fills the card
            margin=dict(l=0, r=0, t=10, b=0),

            # Chart height
            height=320,

            # X-axis styling
            xaxis=dict(
                showgrid=False,                # no vertical grid lines
                linecolor=COLORS["border"],
                tickfont=dict(color=COLORS["text_muted"], size=10),
            ),

            # Y-axis styling
            yaxis=dict(
                title="AUD/MWh",
                titlefont=dict(color=COLORS["text_muted"], size=10),
                gridcolor=COLORS["border_light"],   # subtle horizontal grid
                gridwidth=0.5,
                zeroline=True,                  # show the zero line
                zerolinecolor=COLORS["border"],
                zerolinewidth=0.5,
                tickfont=dict(color=COLORS["text_muted"], size=10),
            ),

            # Hide the legend (we only have one line for now)
            showlegend=False,

            # Hover mode: show info when hovering over the x-axis
            hovermode="x unified",
        )

        # Display the chart in Streamlit.
        # use_container_width=True makes it fill the card's width.
        st.plotly_chart(fig, use_container_width=True, key="main_price_chart")

    # ── Wrap the chart in a dashboard card ──
    # The card adds a title bar and border.
    # modal_content_func will be filled in Step 3 (indicator modal).
    dashboard_card(
        title="Electricity Price — " + region_abbr(),
        content_func=draw_price_chart,
        modal_title="Electricity Price — Detailed View",
        modal_content_func=None,             # ← Step 3 will add this
    )

    # ==============================================================
    # STEPS 3–5: Coming next
    # ==============================================================
    # Step 3: Indicator modal (EMA, BB, RSI toggles)
    # Step 4: Secondary row (heatmap + regional comparison)
    # Step 5: News/alerts card

    st.markdown(
        f"""
        <div style="background-color:{COLORS['bg_card']};
                    border:1px solid {COLORS['border']};
                    border-radius:8px; padding:2rem; margin:0.5rem 0;
                    text-align:center;">
            <p style="color:{COLORS['text_secondary']}; margin:0;">
                Heatmap, regional comparison, and alerts coming in Steps 3–5.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
