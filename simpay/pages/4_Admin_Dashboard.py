"""
pages/4_Admin_Dashboard.py — Network Admin Analytics Dashboard
==============================================================

This page is accessible only with admin credentials (hardcoded for demo).
It demonstrates:
  • Loading the full transaction ledger into a Pandas DataFrame
  • Matplotlib charts: transaction volume over time, success vs failed, amount distribution
  • Anomaly detection: flagging transfers above ₹5,000
  • User account overview table
"""

import streamlit as st
import sys, os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialize_database, get_all_transactions, get_all_users

initialize_database()

st.set_page_config(page_title="Admin Dashboard — SimPay", page_icon="📊", layout="wide")
st.title("📊 Admin Analytics Dashboard")
st.caption("Network-level view of all transactions, anomaly detection, and user statistics.")

# ── Admin authentication (simple hardcoded demo credentials) ─────────────────
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.warning("This page requires Admin credentials.")
    with st.form("admin_login"):
        adm_user = st.text_input("Admin Username")
        adm_pass = st.text_input("Admin Password", type="password")
        adm_submit = st.form_submit_button("Login as Admin")

    if adm_submit:
        if adm_user == ADMIN_USER and adm_pass == ADMIN_PASS:
            st.session_state.admin_logged_in = True
            st.success("Admin login successful!")
            st.rerun()
        else:
            st.error("Invalid admin credentials. (Hint: admin / admin123)")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
transactions = get_all_transactions()
users        = get_all_users()

if st.button("🔄 Refresh Data"):
    transactions = get_all_transactions()
    users        = get_all_users()
    st.rerun()

# ── If no transactions yet, show placeholder ──────────────────────────────────
if not transactions:
    st.info("No transactions in the ledger yet. Make some payments and return here.")
    st.stop()

# ── Build DataFrame ───────────────────────────────────────────────────────────
df = pd.DataFrame(transactions)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"]      = df["timestamp"].dt.date
df["hour"]      = df["timestamp"].dt.hour

ANOMALY_THRESHOLD = 5000.0
df["is_anomalous"] = df["amount"] >= ANOMALY_THRESHOLD

# ── Summary Metrics Row ───────────────────────────────────────────────────────
st.divider()
st.subheader("Network Summary")

total_volume    = df[df["status"] == "SUCCESS"]["amount"].sum()
success_count   = len(df[df["status"] == "SUCCESS"])
failed_count    = len(df[df["status"] == "FAILED"])
anomaly_count   = len(df[df["is_anomalous"] & (df["status"] == "SUCCESS")])

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total Transactions", len(df))
with c2:
    st.metric("Successful", success_count)
with c3:
    st.metric("Failed", failed_count)
with c4:
    st.metric("Total Volume (₹)", f"₹{total_volume:,.2f}")
with c5:
    st.metric("⚠️ Anomalous Txns", anomaly_count)

st.divider()

# ── Chart Layout: Row 1 ───────────────────────────────────────────────────────
st.subheader("Transaction Analytics")
chart_col1, chart_col2 = st.columns(2)

# --- Chart 1: Transaction Volume by Date ---
with chart_col1:
    st.caption("**Daily Transaction Volume (₹)**")
    daily = df[df["status"] == "SUCCESS"].groupby("date")["amount"].sum().reset_index()
    if not daily.empty:
        fig1, ax1 = plt.subplots(figsize=(6, 3.5))
        ax1.bar(daily["date"], daily["amount"], color="#4C72B0", edgecolor="white", linewidth=0.5)
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Total Amount (₹)")
        ax1.set_title("Daily Successful Transaction Volume")
        plt.xticks(rotation=30, ha="right", fontsize=8)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)
    else:
        st.info("No successful transactions to chart yet.")

# --- Chart 2: Success vs. Failed Pie ---
with chart_col2:
    st.caption("**Transaction Status Distribution**")
    status_counts = df["status"].value_counts()
    colors = {"SUCCESS": "#2CA02C", "FAILED": "#D62728"}

    fig2, ax2 = plt.subplots(figsize=(5, 3.5))
    wedge_colors = [colors.get(s, "#7F7F7F") for s in status_counts.index]
    wedges, texts, autotexts = ax2.pie(
        status_counts.values,
        labels=status_counts.index,
        autopct="%1.1f%%",
        colors=wedge_colors,
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    ax2.set_title("Success vs. Failed Transactions")
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

# ── Chart Layout: Row 2 ───────────────────────────────────────────────────────
chart_col3, chart_col4 = st.columns(2)

# --- Chart 3: Amount Distribution Histogram ---
with chart_col3:
    st.caption("**Transaction Amount Distribution**")
    success_amounts = df[df["status"] == "SUCCESS"]["amount"]
    if not success_amounts.empty:
        fig3, ax3 = plt.subplots(figsize=(6, 3.5))
        ax3.hist(success_amounts, bins=15, color="#FF7F0E", edgecolor="white", linewidth=0.5)
        ax3.axvline(ANOMALY_THRESHOLD, color="#D62728", linestyle="--", linewidth=1.5, label=f"Anomaly Threshold (₹{ANOMALY_THRESHOLD:,.0f})")
        ax3.set_xlabel("Amount (₹)")
        ax3.set_ylabel("Frequency")
        ax3.set_title("Transaction Amount Distribution")
        ax3.legend(fontsize=8)
        ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)
    else:
        st.info("No successful transactions to chart yet.")

# --- Chart 4: Transaction Count by Hour ---
with chart_col4:
    st.caption("**Transaction Activity by Hour of Day**")
    hourly = df.groupby("hour").size().reset_index(name="count")
    if not hourly.empty:
        fig4, ax4 = plt.subplots(figsize=(6, 3.5))
        ax4.bar(hourly["hour"], hourly["count"], color="#9467BD", edgecolor="white", linewidth=0.5)
        ax4.set_xlabel("Hour of Day (UTC)")
        ax4.set_ylabel("Transaction Count")
        ax4.set_title("Transaction Activity by Hour")
        ax4.set_xticks(range(0, 24))
        ax4.tick_params(axis='x', labelsize=7)
        plt.tight_layout()
        st.pyplot(fig4)
        plt.close(fig4)
    else:
        st.info("No data to chart yet.")

st.divider()

# ── Anomaly Detection Table ───────────────────────────────────────────────────
st.subheader("⚠️ Anomaly Detection — Large Transfers")
st.caption(f"Transactions flagged when amount ≥ ₹{ANOMALY_THRESHOLD:,.0f} (anomaly threshold).")

anomalous_df = df[df["is_anomalous"] & (df["status"] == "SUCCESS")].copy()

if anomalous_df.empty:
    st.success("No anomalous transactions detected.")
else:
    anomalous_df["timestamp"] = anomalous_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(
        anomalous_df[["id", "sender_upi", "receiver_upi", "amount", "timestamp"]].rename(columns={
            "id": "Txn ID", "sender_upi": "Sender", "receiver_upi": "Receiver",
            "amount": "Amount (₹)", "timestamp": "Timestamp"
        }),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ── Full Ledger Table ─────────────────────────────────────────────────────────
st.subheader("📋 Full Transaction Ledger")
ledger_df = df.copy()
ledger_df["timestamp"] = ledger_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
ledger_df["⚠️"] = ledger_df["is_anomalous"].apply(lambda x: "⚠️" if x else "")
ledger_df["status_icon"] = ledger_df["status"].apply(lambda s: "✅" if s == "SUCCESS" else "❌")

st.dataframe(
    ledger_df[[
        "id", "sender_upi", "receiver_upi", "amount",
        "status_icon", "⚠️", "failure_reason", "timestamp"
    ]].rename(columns={
        "id": "Txn ID", "sender_upi": "Sender", "receiver_upi": "Receiver",
        "amount": "Amount (₹)", "status_icon": "Status", "failure_reason": "Failure Reason",
        "timestamp": "Timestamp"
    }),
    use_container_width=True,
    hide_index=True
)

st.divider()

# ── User Accounts Table ───────────────────────────────────────────────────────
st.subheader("👥 Registered Users")
if users:
    users_df = pd.DataFrame(users)
    users_df["balance"] = users_df["balance"].apply(lambda b: f"₹{b:,.2f}")
    st.dataframe(
        users_df.rename(columns={
            "username": "Username", "upi_id": "UPI ID",
            "balance": "Balance", "created_at": "Registered At"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No users registered yet.")

st.divider()
if st.button("🚪 Admin Logout"):
    st.session_state.admin_logged_in = False
    st.rerun()
