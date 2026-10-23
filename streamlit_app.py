import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Page setup
st.set_page_config(page_title="Lunatics Cricket - Payment Tracker", layout="wide")

st.title("🏏 Lunatics Cricket Club — Payment Tracker")

ADMIN_PASSWORD = "lunatics123"
MATCH_FEE = 140

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize Session Data from Google Sheet once on startup
if "tracker_data" not in st.session_state:
    try:
        raw_df = conn.read(ttl=0)
        st.session_state.tracker_data = raw_df
    except Exception:
        # Fallback squad list if connection fails
        PLAYERS = [
            "Kurt Koopman", "Bjorn Harmse", "Earl Koopman", "Zamile Mqu",
            "Paul Steyn", "Regan Koopman", "Sherwon Tarentaal", "Ashwin Isaacs",
            "Roland Meder", "Rejean Maralack", "Rafique Gool", "Jay-Dee Kellies",
            "Brandon Gordon"
        ]
        st.session_state.tracker_data = pd.DataFrame({
            "Player": PLAYERS,
            "Total Paid (R)": [0.0] * len(PLAYERS)
        })

df = st.session_state.tracker_data

# Ensure fixture columns are boolean
for col in df.columns:
    if col not in ["Player", "Total Paid (R)"]:
        df[col] = df[col].astype(bool)

# --- SIDEBAR: Admin Controls ---
st.sidebar.header("🔒 Admin Access")
user_pwd = st.sidebar.text_input("Enter Admin Password to Edit", type="password")
is_admin = (user_pwd == ADMIN_PASSWORD)

if is_admin:
    st.sidebar.success("Admin Unlocked ✅")
    
    # 1. ADD FIXTURE
    st.sidebar.header("➕ Add New Fixture")
    fixture_name = st.sidebar.text_input("Fixture Name (e.g., Misfits, Match 3)")

    if st.sidebar.button("Add Fixture"):
        if fixture_name and fixture_name not in df.columns:
            df[fixture_name] = False
            st.session_state.tracker_data = df
            st.sidebar.success(f"Added fixture '{fixture_name}'!")
            st.rerun()
        elif fixture_name in df.columns:
            st.sidebar.warning("Fixture already exists!")
        else:
            st.sidebar.error("Please enter a fixture name.")

    # 2. DELETE FIXTURE
    st.sidebar.header("🗑️ Delete Fixture")
    existing_fixtures = [c for c in df.columns if c not in ["Player", "Total Paid (R)"]]
    if existing_fixtures:
        fixture_to_remove = st.sidebar.selectbox("Select fixture to remove", existing_fixtures)
        if st.sidebar.button("Remove Selected Fixture"):
            df = df.drop(columns=[fixture_to_remove])
            st.session_state.tracker_data = df
            st.sidebar.success(f"Removed '{fixture_to_remove}'")
            st.rerun()

# --- MAIN TABLE ---
st.subheader("📋 Match Attendance & Payments")

if is_admin:
    st.info("🔓 Admin Mode Active: You can edit match ticks and payments below.")
    edited_df = st.data_editor(
        df,
        column_config={
            "Player": st.column_config.TextColumn("Player", disabled=True),
            "Total Paid (R)": st.column_config.NumberColumn("Total Paid (R)", min_value=0, step=10, format="R %d"),
        },
        disabled=["Player"],
        hide_index=True,
        use_container_width=True
    )
    st.session_state.tracker_data = edited_df
else:
    st.warning("👁️ Read-Only Mode: Log in via sidebar to edit.")
    st.dataframe(df, hide_index=True, use_container_width=True)
    edited_df = df

# --- CALCULATIONS & DASHBOARD ---
fixture_cols = [c for c in edited_df.columns if c not in ["Player", "Total Paid (R)"]]
games_played = edited_df[fixture_cols].sum(axis=1) if fixture_cols else 0
total_owed = games_played * MATCH_FEE
total_paid = pd.to_numeric(edited_df["Total Paid (R)"], errors='coerce').fillna(0)
balance = total_owed - total_paid

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

# Export/Backup Option
if is_admin:
    st.sidebar.markdown("---")
    csv_data = edited_df.to_csv(index=False)
    st.sidebar.download_button(
        label="📥 Download CSV Backup",
        data=csv_data,
        file_name="lunatics_payment_tracker.csv",
        mime="text/csv"
    )
