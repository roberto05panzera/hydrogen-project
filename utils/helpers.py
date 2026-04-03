"""
Helpers Module — Shared Utilities
==================================
Small reusable functions that don't belong in a specific module.
Things like formatting, unit conversions, constants, styling, etc.

Usage:
    from utils.helpers import format_currency, AUSTRALIAN_REGIONS
    from utils.helpers import inject_custom_css, get_plotly_template, render_kpi_bar
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# NEM regions with display names and coordinates (for weather API)
AUSTRALIAN_REGIONS = {
    "NSW1": {"name": "New South Wales", "lat": -33.87, "lon": 151.21},
    "VIC1": {"name": "Victoria", "lat": -37.81, "lon": 144.96},
    "QLD1": {"name": "Queensland", "lat": -27.47, "lon": 153.03},
    "SA1":  {"name": "South Australia", "lat": -34.93, "lon": 138.60},
    "TAS1": {"name": "Tasmania", "lat": -42.88, "lon": 147.33},
}

# Default electrolyzer parameters (from NREL H2A model)
DEFAULT_EFFICIENCY_KWH_PER_KG = 52.5   # kWh per kg H2 (PEM electrolyzer)
DEFAULT_CAPACITY_MW = 10                # 10 MW electrolyzer
DEFAULT_TARGET_H2_KG = 500             # 500 kg target production


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_currency(value: float, currency: str = "AUD") -> str:
    """Format a number as currency, e.g. 'AUD 1,234.56'."""
    return f"{currency} {value:,.2f}"


def format_price_per_kg(total_cost: float, total_kg: float) -> str:
    """Calculate and format the cost per kg of H2."""
    if total_kg == 0:
        return "N/A"
    cost_per_kg = total_cost / total_kg
    return f"AUD {cost_per_kg:.2f}/kg"


def hours_to_text(hours: int) -> str:
    """Convert hours to a readable string, e.g. '2 days 4 hours'."""
    days = hours // 24
    remaining = hours % 24
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if remaining > 0:
        parts.append(f"{remaining} hour{'s' if remaining != 1 else ''}")
    return " ".join(parts) if parts else "0 hours"


# ---------------------------------------------------------------------------
# Styling — Dark Dashboard Theme
# ---------------------------------------------------------------------------

# Color palette (shared across all pages and charts)
COLORS = {
    "bg_main":      "#0E1117",
    "bg_card":      "#1A1F2E",
    "bg_card_alt":  "#161B26",
    "accent":       "#00D4AA",
    "accent_light": "#4ECDC4",
    "red":          "#FF6B6B",
    "amber":        "#FFD93D",
    "text":         "#E0E0E0",
    "text_muted":   "#8B95A5",
    "border":       "#2A2F3E",
    "grid":         "#2A2F3E",
    "green":        "#00D4AA",
    "purple":       "#6C5CE7",
}


def inject_custom_css():
    """Inject the master dark-dashboard CSS. Call once at the top of every page."""
    st.markdown("""<style>
    /* --- KPI metric cards --- */
    [data-testid="stMetric"] {
        background: #1A1F2E;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 3px solid #00D4AA;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8B95A5;
    }

    /* --- Sidebar branding area --- */
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }

    /* --- Main content padding --- */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    /* --- Expander cards --- */
    [data-testid="stExpander"] {
        background: #1A1F2E;
        border: 1px solid #2A2F3E;
        border-radius: 8px;
    }

    /* --- Tab styling --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #161B26;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        color: #8B95A5;
    }

    /* --- Radio as button group --- */
    div[data-testid="stRadio"] > div {
        gap: 0 !important;
    }
    div[data-testid="stRadio"] > div > label {
        background: #161B26;
        border: 1px solid #2A2F3E;
        padding: 6px 16px;
        margin: 0;
        color: #8B95A5;
        cursor: pointer;
    }
    div[data-testid="stRadio"] > div > label:first-child {
        border-radius: 6px 0 0 6px;
    }
    div[data-testid="stRadio"] > div > label:last-child {
        border-radius: 0 6px 6px 0;
    }

    /* --- Hide default header --- */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* --- Download button --- */
    [data-testid="stDownloadButton"] > button {
        background: #1A1F2E;
        border: 1px solid #2A2F3E;
        color: #E0E0E0;
    }
    [data-testid="stDownloadButton"] > button:hover {
        border-color: #00D4AA;
        color: #00D4AA;
    }

    /* --- Divider --- */
    hr {
        border-color: #2A2F3E;
    }

    /* --- Custom card class --- */
    .dashboard-card {
        background: #1A1F2E;
        border: 1px solid #2A2F3E;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .dashboard-card h4 {
        margin: 0 0 12px 0;
        color: #E0E0E0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* --- Status bar --- */
    .status-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #161B26;
        border-top: 1px solid #2A2F3E;
        padding: 6px 24px;
        font-size: 0.75rem;
        color: #8B95A5;
        display: flex;
        justify-content: space-between;
        z-index: 999;
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .status-dot.connected { background: #00D4AA; }
    .status-dot.disconnected { background: #FF6B6B; }

    /* --- News article row --- */
    .news-item {
        padding: 10px 0;
        border-bottom: 1px solid #2A2F3E;
    }
    .news-item:last-child { border-bottom: none; }
    .news-title { color: #E0E0E0; font-size: 0.85rem; margin-bottom: 4px; }
    .news-meta { color: #8B95A5; font-size: 0.7rem; }

    /* --- Weather grid item --- */
    .weather-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #2A2F3E;
    }
    .weather-item:last-child { border-bottom: none; }
    .weather-label { color: #8B95A5; font-size: 0.8rem; }
    .weather-value { color: #E0E0E0; font-size: 0.85rem; font-weight: 600; }

    /* --- Timeline blocks --- */
    .timeline-container {
        display: flex;
        width: 100%;
        border-radius: 6px;
        overflow: hidden;
        margin: 8px 0;
    }
    .timeline-block {
        padding: 10px 4px;
        text-align: center;
        font-size: 0.65rem;
        font-weight: 600;
    }
    .timeline-produce {
        background: #00D4AA;
        color: #0E1117;
    }
    .timeline-idle {
        background: #1A1F2E;
        color: #8B95A5;
        border: 1px solid #2A2F3E;
    }

    /* --- Scenario table --- */
    .scenario-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
    }
    .scenario-table th {
        background: #161B26;
        color: #8B95A5;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 2px solid #2A2F3E;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.04em;
    }
    .scenario-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #2A2F3E;
        color: #E0E0E0;
    }
    .scenario-table tr:hover {
        background: #161B26;
    }
    .scenario-table .highlight {
        color: #00D4AA;
        font-weight: 600;
    }
    </style>""", unsafe_allow_html=True)


def get_plotly_template():
    """Return a Plotly layout dict for the dark dashboard theme.

    Usage:
        fig.update_layout(**get_plotly_template())
    """
    return dict(
        paper_bgcolor=COLORS["bg_card"],
        plot_bgcolor=COLORS["bg_main"],
        font=dict(color=COLORS["text"], family="sans-serif", size=12),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor="#3A3F4E",
            showgrid=True,
            gridwidth=1,
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor="#3A3F4E",
            showgrid=True,
            gridwidth=1,
        ),
        colorway=[
            COLORS["accent"], COLORS["red"], COLORS["accent_light"],
            COLORS["amber"], COLORS["purple"], "#A8E6CF",
        ],
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["text"]),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_card"],
            font_color=COLORS["text"],
            bordercolor=COLORS["border"],
        ),
        margin=dict(l=40, r=20, t=40, b=40),
    )


def render_kpi_bar(metrics: list[dict]):
    """Render a row of KPI metric cards.

    Each dict in *metrics* should have:
        label  – e.g. "SPOT PRICE"
        value  – e.g. "-$12.40"
        unit   – e.g. "AUD/MWh"
        delta  – e.g. "-134%"  (optional)
        delta_color – "normal" | "inverse" | "off" (optional, default "normal")
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
                delta_color=m.get("delta_color", "normal"),
            )
            if m.get("unit"):
                st.caption(m["unit"])


def render_status_bar(connected: bool = True, last_sync: str = "14:32 AEST"):
    """Render a fixed status bar at the bottom of the page."""
    dot_class = "connected" if connected else "disconnected"
    label = "API Connected" if connected else "Disconnected"
    st.markdown(
        f"""<div class="status-bar">
            <span><span class="status-dot {dot_class}"></span>{label}</span>
            <span>Last sync: {last_sync}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def render_card_header(title: str, subtitle: str = ""):
    """Render a styled section header for a dashboard card."""
    sub = f'<span style="color:#8B95A5; font-size:0.75rem; margin-left:8px;">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f'<h4 style="color:#E0E0E0; font-size:0.9rem; text-transform:uppercase; '
        f'letter-spacing:0.04em; margin:0 0 8px 0;">{title}{sub}</h4>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    """Render the sidebar branding block."""
    st.sidebar.markdown(
        """<div style="text-align:center; padding:8px 0 16px 0; border-bottom:1px solid #2A2F3E; margin-bottom:16px;">
            <div style="font-size:1.4rem; font-weight:700; color:#00D4AA;">H2 Optimizer</div>
            <div style="font-size:0.7rem; color:#8B95A5; margin-top:2px;">v1.0</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Group 4.04 — *Not Found*")
    st.sidebar.caption("Fundamentals of Computer Science | HS 2026")


def get_placeholder_kpis(region: str = "SA1") -> list[dict]:
    """Placeholder KPI data for the dashboard top bar.

    Returns a list of 5 KPI dicts ready for render_kpi_bar().
    """
    # PLUG: dashboard_kpis — Replace hardcoded values with live data from utils/api.py
    return [
        {"label": "SPOT PRICE",  "value": "-$12.40", "unit": "AUD/MWh", "delta": "-134%",  "delta_color": "inverse"},
        {"label": "24H AVG",     "value": "$38.70",  "unit": "AUD/MWh", "delta": "-8.2%",   "delta_color": "normal"},
        {"label": "24H HIGH",    "value": "$89.40",  "unit": "AUD/MWh", "delta": "+12%",    "delta_color": "normal"},
        {"label": "NEG. HOURS",  "value": "18",      "unit": f"of 168 (7d) — {region}", "delta": "+23%", "delta_color": "inverse"},
        {"label": "WIND OUTPUT", "value": "4.2 GW",  "unit": f"{AUSTRALIAN_REGIONS.get(region, {}).get('name', region)}", "delta": "High", "delta_color": "off"},
    ]
