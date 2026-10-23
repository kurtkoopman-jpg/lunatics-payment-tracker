import streamlit as st
import pandas as pd

# Page setup
st.set_page_config(page_title="Lunatics Cricket - Payment Tracker", layout="wide")

st.title("🏏 Lunatics Cricket Club — Payment Tracker")

# 1. Squad List
PLAYERS = [
    "Kurt Koopman", "Bjorn Harmse", "Earl Koopman", "Zamile Mqu",
    "Paul Steyn", "Regan Koopman", "Sherwon Tarentaal", "Ashwin Isaacs",
    "Roland Meder", "Rejean Maralack", "Rafique Gool", "Jay-Dee Kellies",
    "Brandon Gordon"
]

MATCH_FEE = 140

# 2. Initialize Data Frame
if "tracker_data" not in st.session_state:
    st.session_state.tracker_data = pd.DataFrame({
        "Player": PLAYERS,
        "Total Paid (R)": [0.0] * len(PLAYERS)
    })

# --- SIDEBAR: Add Match Fixtures ---
st.sidebar.header("➕ Add New Fixture")
fixture_name = st.sidebar.text_input("Fixture Name (e.g., Misfits, Match 3)")

if st.sidebar.button("Add Fixture"):
    if fixture_name and fixture_name not in st.session_state.tracker_data.columns:
        st.session_state.tracker_data[fixture_name] = False
        st.sidebar.success(f"Added fixture: {fixture_name}")
    elif fixture_name in st.session_state.tracker_data.columns:
        st.sidebar.warning("That fixture already exists!")
    else:
        st.sidebar.error("Please enter a fixture name.")

# --- MAIN DATA EDITOR ---
st.subheader("📋 Match Attendance & Payments")
st.write("Tick the boxes for players who played each match. Enter total payments made in the **Total Paid (R)** column.")

edited_df = st.data_editor(
    st.session_state.tracker_data,
    column_config={
        "Player": st.column_config.TextColumn("Player", disabled=True),
        "Total Paid (R)": st.column_config.NumberColumn("Total Paid (R)", min_value=0, step=10, format="R %d"),
    },
    disabled=["Player"],
    hide_index=True,
    use_container_width=True
)

st.session_state.tracker_data = edited_df

# --- CALCULATIONS ---
fixture_cols = [c for c in edited_df.columns if c not in ["Player", "Total Paid (R)"]]

games_played = edited_df[fixture_cols].sum(axis=1) if fixture_cols else 0
total_owed = games_played * MATCH_FEE
total_paid = edited_df["Total Paid (R)"]
balance = total_owed - total_paid

# --- DASHBOARD ---
st.markdown("---")
st.subheader("📊 Summary Dashboard")

summary_df = pd.DataFrame({
    "Player": edited_df["Player"],
    "Matches Played": games_played,
    "Total Owed (R)": total_owed,
    "Total Paid (R)": total_paid,
    "Balance (R)": balance
})

def get_status(bal):
    if bal < 0:
        return f"In Credit (R {abs(bal):.0f}) 🟢"
    elif bal == 0:
        return "Squared Up ✅"
    else:
        return f"Owes R {bal:.0f} 🔴"

summary_df["Status"] = summary_df["Balance (R)"].apply(get_status)

col1, col2, col3 = st.columns(3)
col1.metric("Total Fees Owed", f"R {summary_df['Total Owed (R)'].sum():,.0f}")
col2.metric("Total Payments Collected", f"R {summary_df['Total Paid (R)'].sum():,.0f}")
col3.metric("Outstanding Balance", f"R {summary_df['Balance (R)'].sum():,.0f}")

st.dataframe(summary_df, hide_index=True, use_container_width=True)

# --- BACKUP DATA ---
st.sidebar.markdown("---")
csv_data = edited_df.to_csv(index=False)
st.sidebar.download_button(
    label="📥 Backup Data (Download CSV)",
    data=csv_data,
    file_name="lunatics_payment_tracker.csv",
    mime="text/csv"
)
