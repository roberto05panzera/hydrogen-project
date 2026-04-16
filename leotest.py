import io
from typing import List, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


EXPECTED_EXCEL_COLUMNS = ["Cost Item", "Amount (AUD)"]


def _init_session_state() -> None:
    """Initialize session state keys used by this block."""
    if "extra_cost_items" not in st.session_state:
        st.session_state["extra_cost_items"] = []

    if "manual_cost_label" not in st.session_state:
        st.session_state["manual_cost_label"] = ""

    if "manual_cost_amount" not in st.session_state:
        st.session_state["manual_cost_amount"] = 0.0

    # Tracks uploaded file so we don't duplicate rows on rerun
    if "processed_cost_upload_name" not in st.session_state:
        st.session_state["processed_cost_upload_name"] = None



def _normalize_cost_items(df: pd.DataFrame) -> List[Dict[str, float]]:
    """Validate and transform uploaded Excel rows into the expected session-state format."""
    missing = [col for col in EXPECTED_EXCEL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected columns: {', '.join(EXPECTED_EXCEL_COLUMNS)}"
        )

    cleaned = df[EXPECTED_EXCEL_COLUMNS].copy()
    cleaned["Cost Item"] = cleaned["Cost Item"].astype(str).str.strip()
    cleaned["Amount (AUD)"] = pd.to_numeric(cleaned["Amount (AUD)"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Cost Item", "Amount (AUD)"])
    cleaned = cleaned[cleaned["Cost Item"] != ""]

    items: List[Dict[str, float]] = []
    for _, row in cleaned.iterrows():
        items.append(
            {
                "label": str(row["Cost Item"]),
                "amount_aud": float(row["Amount (AUD)"]),
            }
        )
    return items



def _add_manual_item() -> None:
    """Append a manually entered cost item to session state."""
    label = st.session_state.get("manual_cost_label", "").strip()
    amount = float(st.session_state.get("manual_cost_amount", 0.0))

    if not label:
        st.warning("Please enter a cost item name before adding it.")
        return

    st.session_state["extra_cost_items"].append(
        {
            "label": label,
            "amount_aud": amount,
        }
    )

    # Clear inputs after adding
    st.session_state["manual_cost_label"] = ""
    st.session_state["manual_cost_amount"] = 0.0



def _remove_item(index: int) -> None:
    """Remove a cost item by index."""
    items = st.session_state.get("extra_cost_items", [])
    if 0 <= index < len(items):
        items.pop(index)
        st.session_state["extra_cost_items"] = items



def _build_donut_chart(total_cost_aud: float, extra_cost_items: List[Dict[str, float]]) -> go.Figure:
    """Create the donut chart using electricity cost + extra cost items."""
    all_labels = ["Electricity Cost"] + [item["label"] for item in extra_cost_items]
    all_values = [float(total_cost_aud)] + [float(item["amount_aud"]) for item in extra_cost_items]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=all_labels,
                values=all_values,
                hole=0.5,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>AUD %{value:,.2f}<br>%{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=500,
        legend_title_text="Cost Components",
    )
    return fig



def render_cost_breakdown() -> None:
    """Render Block 6 - Cost Breakdown & Donut Chart."""
    _init_session_state()

    st.subheader("Full Cost Breakdown")
    st.caption("Add extra cost items manually or upload them from an Excel file to see the full cost split.")

    total_cost_aud = st.session_state.get("total_cost_aud")
    if total_cost_aud is None:
        total_cost_aud = 0.0
        st.info("Electricity cost could not be computed yet, so a placeholder value of 0.0 AUD is being used.")

    # ----- Manual input section -----
    st.markdown("### Add Cost Items Manually")
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.text_input(
            "Cost Item",
            key="manual_cost_label",
            placeholder="e.g. Electrolyser CAPEX",
        )
    with col2:
        st.number_input(
            "Amount (AUD)",
            key="manual_cost_amount",
            min_value=0.0,
            step=100.0,
            format="%.2f",
        )
    with col3:
        st.write("")
        st.write("")
        st.button("Add cost item", use_container_width=True, on_click=_add_manual_item)

    # ----- Excel upload section -----
    st.markdown("### Upload Excel Cost File")
    uploaded_file = st.file_uploader(
        "Upload an Excel file (.xlsx)",
        type=["xlsx"],
        help='Expected columns: "Cost Item" and "Amount (AUD)"',
    )

    if uploaded_file is not None:
        # Only process once per newly uploaded file name to avoid duplicates on rerun
        current_name = uploaded_file.name
        if st.session_state.get("processed_cost_upload_name") != current_name:
            try:
                file_bytes = uploaded_file.read()
                df = pd.read_excel(io.BytesIO(file_bytes))
                uploaded_items = _normalize_cost_items(df)

                st.session_state["extra_cost_items"].extend(uploaded_items)
                st.session_state["processed_cost_upload_name"] = current_name
                st.success(f"Uploaded {len(uploaded_items)} cost item(s) from {current_name}.")
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Could not read the uploaded Excel file: {exc}")

    # ----- Review current items -----
    st.markdown("### Current Additional Cost Items")
    extra_cost_items = st.session_state.get("extra_cost_items", [])

    if not extra_cost_items:
        st.write("No additional cost items added yet.")
    else:
        for idx, item in enumerate(extra_cost_items):
            item_col1, item_col2, item_col3 = st.columns([3, 2, 1])
            with item_col1:
                st.write(item["label"])
            with item_col2:
                st.write(f"AUD {item['amount_aud']:,.2f}")
            with item_col3:
                st.button("Remove", key=f"remove_cost_item_{idx}", on_click=_remove_item, args=(idx,))

        extra_total = sum(float(item["amount_aud"]) for item in extra_cost_items)
        grand_total = float(total_cost_aud) + extra_total

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Electricity Cost", f"AUD {float(total_cost_aud):,.2f}")
        metric_col2.metric("Additional Costs", f"AUD {extra_total:,.2f}")
        metric_col3.metric("Grand Total", f"AUD {grand_total:,.2f}")

    # ----- Donut chart -----
    st.markdown("### Donut Chart")
    fig = _build_donut_chart(float(total_cost_aud), extra_cost_items)
    st.plotly_chart(fig, use_container_width=True)


# Optional local test helper
if __name__ == "__main__":
    st.set_page_config(page_title="Block 6 Test", layout="wide")
    st.session_state.setdefault("total_cost_aud", 1850.75)
    render_cost_breakdown()
