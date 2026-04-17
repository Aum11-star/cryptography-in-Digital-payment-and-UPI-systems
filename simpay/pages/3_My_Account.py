"""
pages/3_My_Account.py — User Account Dashboard
===============================================

Shows the logged-in user's account information:
  • UPI ID and current balance
  • RSA public key
  • Personal transaction history
"""

import streamlit as st
import sys, os, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialize_database, get_user_by_upi, get_user_transactions

initialize_database()

st.set_page_config(page_title="My Account — SimPay", page_icon="👤", layout="wide")
st.title("👤 My Account")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user" not in st.session_state or not st.session_state.user:
    st.warning("You must be logged in to view your account.")
    st.page_link("pages/1_Login_Register.py", label="Go to Login", icon="🔑")
    st.stop()

# Refresh from DB
user = get_user_by_upi(st.session_state.user["upi_id"])
if user:
    st.session_state.user = user

user = st.session_state.user

# ── Account info ──────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Username", user["username"])
with col2:
    st.metric("UPI ID", user["upi_id"])
with col3:
    st.metric("Balance", f"₹{user['balance']:,.2f}")

st.divider()

# ── Cryptographic Identity ────────────────────────────────────────────────────
st.subheader("🔑 Your Cryptographic Identity")
st.caption(
    "When you registered, a 2048-bit RSA key pair was generated uniquely for your account. "
    "Your public key is shared openly; your private key is stored securely in the system."
)

col_pub, col_priv = st.columns(2)

with col_pub:
    with st.expander("View RSA Public Key"):
        st.code(user.get("public_key", "N/A"), language="text")
        st.caption("Safe to share. Used to encrypt messages intended for you.")

with col_priv:
    with st.expander("View RSA Private Key (Simulated — would be hidden in production)"):
        st.code(user.get("private_key", "N/A"), language="text")
        st.caption("⚠️ In a real system, this key would NEVER be exposed to the UI.")

st.divider()

# ── Transaction History ───────────────────────────────────────────────────────
st.subheader("📋 Transaction History")

transactions = get_user_transactions(user["upi_id"])

if not transactions:
    st.info("No transactions yet. Go to Send Payment to make your first transfer.")
else:
    df = pd.DataFrame(transactions)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Add direction column
    df["direction"] = df.apply(
        lambda r: "⬆️ Sent" if r["sender_upi"] == user["upi_id"] else "⬇️ Received",
        axis=1
    )

    # Color code status
    df["status_icon"] = df["status"].apply(lambda s: "✅" if s == "SUCCESS" else "❌")

    display_df = df[[
        "id", "direction", "sender_upi", "receiver_upi",
        "amount", "status_icon", "failure_reason", "timestamp"
    ]].rename(columns={
        "id": "Txn ID",
        "direction": "Direction",
        "sender_upi": "Sender",
        "receiver_upi": "Receiver",
        "amount": "Amount (₹)",
        "status_icon": "Status",
        "failure_reason": "Failure Reason",
        "timestamp": "Timestamp"
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Summary metrics
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    sent_df = df[(df["sender_upi"] == user["upi_id"]) & (df["status"] == "SUCCESS")]
    recv_df = df[(df["receiver_upi"] == user["upi_id"]) & (df["status"] == "SUCCESS")]

    with c1:
        st.metric("Total Sent", f"₹{sent_df['amount'].sum():,.2f}")
    with c2:
        st.metric("Total Received", f"₹{recv_df['amount'].sum():,.2f}")
    with c3:
        st.metric("Successful Txns", len(df[df["status"] == "SUCCESS"]))
    with c4:
        st.metric("Failed Txns", len(df[df["status"] == "FAILED"]))
