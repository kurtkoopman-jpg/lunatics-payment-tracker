import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Lunatics Cricket - Payment Tracker", layout="wide")
st.title("🏏 Lunatics Cricket Club — Payment Tracker")

ADMIN_PASSWORD = "lunatics123"
MATCH_FEE = 140
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ciOxcRHuexPgvkcgcvJTmWXwHpnmPm_TXpSKLbOuT_U/edit"

# 1. Authorize gspread client
@st.cache_resource
def get_gspread_client():
    sec = st.secrets["connections"]["gsheets"]
    creds_dict = {
        "type": sec.get("type", "service_account"),
        "project_id": sec["project_id"],
        "private_key_id": sec["private_key_id"],
        "private_key": sec["private_key"].replace("\\n", "\n"),
        "client_email": sec["client_email"],
        "client_id": sec["client_id"],
        "auth_uri": sec.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": sec.get("token_uri", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": sec.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": sec.get("client_x509_cert_url", ""),
    }
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

# 2. Cache data fetching for 60 seconds to prevent API Quota Limits (429)
@st.cache_data(ttl=60)
def load_data():
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.sheet1
    data = worksheet.get_all_records()
    if data:
        return pd.DataFrame(data)
    return pd.DataFrame(columns=["Player", "Total Paid (R)"])

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Connection Error Details: {type(e).__name__} — {str(e)}")
    st.exception(e)
    st.stop()

# Ensure boolean types for match attendance
for col in df.columns:
    if col not in ["Player", "Total Paid (R)"]:
        df[col] = df[col].astype(bool)

# --- SIDEBAR: Admin Controls ---
st.sidebar.header("🔒 Admin Access")
user_pwd = st.sidebar.text_input("Enter Admin Password to Edit", type="password")
is_admin = (user_pwd == ADMIN_PASSWORD)

def save_to_sheets(updated_df):
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.sheet1
    
    export_df = updated_df.copy()
    for col in export_df.columns:
        if col not in ["Player", "Total Paid (R)"]:
            export_df[col] = export_df[col].astype(str)
            
    worksheet.clear()
    worksheet.update([export_df.columns.values.tolist()] + export_df.values.tolist())
    st.cache_data.clear()  # Clear cache after saving so new data reflects instantly

if is_admin:
    st.sidebar.success("Admin Unlocked ✅")
    
    # 1. ADD FIXTURE
    st.sidebar.header("➕ Add New Fixture")
    fixture_name = st.sidebar.text_input("Fixture Name (e.g., Misfits, Match 3)")

    if st.sidebar.button("Add Fixture"):
        if fixture_name and fixture_name not in df.columns:
            df[fixture_name] = False
            save_to_sheets(df)
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
            save_to_sheets(df)
            st.sidebar.success(f"Removed '{fixture_to_remove}'")
            st.rerun()

# --- MAIN TABLE ---
st.subheader("📋 Match Attendance & Payments")

if is_admin:
    st.info("🔓 Admin Mode Active: Edits will automatically sync to Google Sheets.")
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
    
    if not edited_df.equals(df):
        save_to_sheets(edited_df)
        st.toast("Saved changes to Google Sheets! ✅")
        st.rerun()
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
