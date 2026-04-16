import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.dialog("Add Cost Item")
def add_cost_dialog():
    label = st.text_input("Cost Item", placeholder="e.g. Water Cost")
    amount = st.number_input("Amount (AUD)", min_value=0.0, step=100.0, format="%.2f")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", use_container_width=True):
            if label.strip():
                st.session_state.extra_cost_items.append(
                    {"label": label.strip(), "amount": amount}
                )
                st.rerun()
            else:
                st.warning("Please enter a cost item name.")
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_cost_breakdown():
    st.subheader("Full Cost Breakdown")

    if "extra_cost_items" not in st.session_state:
        st.session_state.extra_cost_items = []

    if "uploaded_excel_name" not in st.session_state:
        st.session_state.uploaded_excel_name = ""

    total_cost_aud = st.session_state.get("total_cost_aud", 0.0)

    m1, m2, m3 = st.columns(3)
    extra_total = sum(item["amount"] for item in st.session_state.extra_cost_items)
    grand_total = total_cost_aud + extra_total
    m1.metric("Electricity Cost", f"AUD {total_cost_aud:,.2f}")
    m2.metric("Additional Costs", f"AUD {extra_total:,.2f}")
    m3.metric("Grand Total", f"AUD {grand_total:,.2f}")

    b1, b2 = st.columns(2)

    with b1:
        if st.button("Add manually", use_container_width=True):
            add_cost_dialog()

    with b2:
        uploaded_file = st.file_uploader(
            "Upload Excel",
            type=["xlsx"],
            label_visibility="collapsed",
        )

    if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_excel_name:
        try:
            df = pd.read_excel(uploaded_file)
            if "Cost Item" in df.columns and "Amount (AUD)" in df.columns:
                for _, row in df.iterrows():
                    label = str(row["Cost Item"]).strip()
                    if label:
                        st.session_state.extra_cost_items.append(
                            {"label": label, "amount": float(row["Amount (AUD)"])}
                        )
                st.session_state.uploaded_excel_name = uploaded_file.name
                st.success(f"Uploaded {uploaded_file.name}")
                st.rerun()
            else:
                st.error('Excel file must contain "Cost Item" and "Amount (AUD)" columns.')
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("### Current Items")
        if not st.session_state.extra_cost_items:
            st.write("No extra cost items yet.")
        else:
            for i, item in enumerate(st.session_state.extra_cost_items):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(item["label"])
                c2.write(f"AUD {item['amount']:,.2f}")
                if c3.button("Remove", key=f"remove_{i}"):
                    st.session_state.extra_cost_items.pop(i)
                    st.rerun()

    with right:
        st.markdown("### Cost Donut Chart")
        labels = ["Electricity Cost"] + [item["label"] for item in st.session_state.extra_cost_items]
        values = [total_cost_aud] + [item["amount"] for item in st.session_state.extra_cost_items]

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.6)])
        fig.update_layout(height=420, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)


st.set_page_config(page_title="Block 6 Test", layout="wide")
st.session_state.setdefault("total_cost_aud", 0.0)
render_cost_breakdown()
