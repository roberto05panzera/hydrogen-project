import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.dialog("Add Cost Item") #Opens a popup dialog titled 'add cost item'
def add_cost_dialog(): 
    label = st.text_input("Cost Item", placeholder="e.g. Water Cost") # label and amount are where the user inout takes place. as variables the store whatever is typed in teh box 
    amount = st.number_input("Amount (AUD)", min_value=0.0, step=100.0, format="%.2f") 

    c1, c2 = st.columns(2) #creates 2 columns next to eachother, and storse them in variables c1 and c2
    with c1: #firzt item inside column 1 
        if st.button("Save", use_container_width=True): #Button that if clicked, runs the code 
            if label.strip(): #No check if  the button is empty. Returns "clean" string by removing spaces.  # in this case, ython echecks whetehre there is still text after removing spaces. If the answer is yes, python assigns teh cost name to label and the number (value AUD) to teh "amount" variable. 
                st.session_state.extra_cost_items.append(
                    {"label": label.strip(), "amount": amount}
                ) #adds teh data label and amount to the list of extra cost items. 
                st.rerun() # reloads the app and the list appears on screen. 
            else:
                st.warning("Please enter a cost item name.") #if no text is left, warning message appears.
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun() # refreshes the app, which closes the dialog without saving anything. Script is basically started from teh top. 


def render_cost_breakdown(): 
    st.subheader("Full Cost Breakdown") # both are just text, and give instructions. There is no user interaction here
    st.caption("Add extra costs manually or upload an Excel file.") 

    if "extra_cost_items" not in st.session_state: #Python checks whether session_state already has items called extra_cost_items If it does not exist, that means the app has no saved list for extra cost. then the next line creates it as an e,mpty öost, so the app can store itsms inside it. 
        st.session_state.extra_cost_items = []

    if "uploaded_excel_name" not in st.session_state: #same thing as extra_cost_item, but checks for excel. 
        st.session_state.uploaded_excel_name = "" #empty strng. Its teh one showing up after one uplaods it. 

    has_electricity_cost = "total_cost_au" in st.session_state #checks if electricity cost value already exists in memry. 
    total_cost_au = st.session_state.get("total_cost_au", 0.0) #if it does not exist, it starts by 0

    extra_total = sum(item["amount"] for item in st.session_state.extra_cost_items)
    grand_total = total_cost_au + extra_total

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Electricity Cost",
        f"AUD {total_cost_au:,.2f}" if has_electricity_cost else "Not available yet",
    )
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
                            {
                                "label": label,
                                "amount": float(row["Amount (AUD)"]),
                            }
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

        labels = []
        values = []

        if has_electricity_cost:
            labels.append("Electricity Cost")
            values.append(total_cost_au)

        for item in st.session_state.extra_cost_items:
            labels.append(item["label"])
            values.append(item["amount"])

        if values:
            fig = go.Figure(
                data=[go.Pie(labels=labels, values=values, hole=0.6)]
            )
            fig.update_layout(height=420, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cost data to display yet.")


st.set_page_config(page_title="Block 6 Test", layout="wide")

# Remove this line later when Block 4 is connected

render_cost_breakdown()
