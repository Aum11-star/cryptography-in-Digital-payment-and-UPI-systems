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
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialize_database, get_user_by_upi, get_user_transactions
from ui_effects import inject_global_effects

initialize_database()

st.set_page_config(page_title="My Account — SimPay", page_icon="👤", layout="wide")
inject_global_effects()
st.markdown("""
<style>
    .account-card, .txn-card {
        background: var(--simpay-card);
        border: 1px solid var(--simpay-border);
        padding: 1.2rem 1.4rem;
        border-radius: 16px;
        box-shadow: 0 10px 22px rgba(54, 82, 164, 0.15);
        animation: simpay-pop 0.45s ease;
    }
    .info-card {
        background: linear-gradient(135deg, #5974ff 0%, #5e49b4 50%, #2f93ff 100%);
        padding: 1.6rem;
        border-radius: 18px;
        box-shadow: 0 16px 32px rgba(62, 97, 213, 0.3);
        transition: transform 0.2s ease;
    }
    .info-card:hover { transform: translateY(-3px); }
    .key-card {
        background: var(--simpay-card);
        border: 1px solid var(--simpay-border);
        border-left: 5px solid #5b7aff;
        border-radius: 14px;
        padding: 0.5rem;
    }
    .key-card p, .account-card p, [data-testid="stMarkdownContainer"] p {
        color: var(--simpay-text) !important;
    }
    .streamlit-expanderHeader {
        background: rgba(94, 125, 255, 0.12) !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='simpay-title'>👤 My Account</h1>", unsafe_allow_html=True)

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
st.markdown("""
<div class="account-card" style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
    <h3 style="color: white; -webkit-text-fill-color: unset;">🎉 Welcome to Your Account Dashboard</h3>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="info-card">
        <h3 style="color: white; -webkit-text-fill-color: unset; font-size: 1.2em;">👤 Username</h3>
        <h2 style="color: white; -webkit-text-fill-color: unset; font-size: 1.8em; margin: 0.5rem 0;">{user['username']}</h2>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="info-card">
        <h3 style="color: white; -webkit-text-fill-color: unset; font-size: 1.2em;">📱 UPI ID</h3>
        <h2 style="color: white; -webkit-text-fill-color: unset; font-size: 1.5em; margin: 0.5rem 0; word-break: break-all;">{user['upi_id']}</h2>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="info-card">
        <h3 style="color: white; -webkit-text-fill-color: unset; font-size: 1.2em;">💰 Balance</h3>
        <h2 style="color: white; -webkit-text-fill-color: unset; font-size: 1.8em; margin: 0.5rem 0;">₹{user['balance']:,.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Cryptographic Identity ────────────────────────────────────────────────────
st.markdown("""
<div class="account-card">
    <h2>🔐 Your Cryptographic Identity</h2>
    <p>When you registered, a 2048-bit RSA key pair was generated uniquely for your account. 
    Your public key is shared openly; your private key is stored securely in the system.</p>
</div>
""", unsafe_allow_html=True)

col_pub, col_priv = st.columns(2)

with col_pub:
    st.markdown('<div class="key-card">', unsafe_allow_html=True)
    with st.expander("🔑 View RSA Public Key"):
        st.code(user.get("public_key", "N/A"), language="text")
        st.caption("✅ Safe to share. Used to encrypt messages intended for you.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_priv:
    st.markdown('<div class="key-card">', unsafe_allow_html=True)
    with st.expander("🔐 View RSA Private Key (Simulated)"):
        st.code(user.get("private_key", "N/A"), language="text")
        st.caption("⚠️ In a real system, this key would NEVER be exposed to the UI.")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ── Transaction History ───────────────────────────────────────────────────────
st.markdown("""
<div class="account-card">
    <h2>📋 Transaction History</h2>
</div>
""", unsafe_allow_html=True)

transactions = get_user_transactions(user["upi_id"])

if not transactions:
    st.info("📊 No transactions yet. Go to Send Payment to make your first transfer.")
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

    st.markdown('<div class="txn-card">', unsafe_allow_html=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Summary metrics
    st.divider()
    st.markdown("""
    <div class="account-card">
        <h2>📊 Transaction Summary</h2>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    sent_df = df[(df["sender_upi"] == user["upi_id"]) & (df["status"] == "SUCCESS")]
    recv_df = df[(df["receiver_upi"] == user["upi_id"]) & (df["status"] == "SUCCESS")]

    with c1:
        st.markdown(f"""
        <div class="info-card" style="background: linear-gradient(135deg, #FF6B6B 0%, #FF8E72 100%);">
            <h3 style="color: white; -webkit-text-fill-color: unset;">⬆️ Total Sent</h3>
            <h2 style="color: white; -webkit-text-fill-color: unset;">₹{sent_df['amount'].sum():,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="info-card" style="background: linear-gradient(135deg, #4C9AFF 0%, #7FD8E3 100%);">
            <h3 style="color: white; -webkit-text-fill-color: unset;">⬇️ Total Received</h3>
            <h2 style="color: white; -webkit-text-fill-color: unset;">₹{recv_df['amount'].sum():,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="info-card" style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);">
            <h3 style="color: white; -webkit-text-fill-color: unset;">✅ Successful</h3>
            <h2 style="color: white; -webkit-text-fill-color: unset;">{len(df[df['status'] == 'SUCCESS'])}</h2>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="info-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h3 style="color: white; -webkit-text-fill-color: unset;">❌ Failed</h3>
            <h2 style="color: white; -webkit-text-fill-color: unset;">{len(df[df['status'] == 'FAILED'])}</h2>
        </div>
        """, unsafe_allow_html=True)

    # Monthly spending box
    st.divider()
    
    # Get current month's first day
    today = datetime.now()
    first_day_of_month = today.replace(day=1)
    first_day_str = first_day_of_month.strftime("%Y-%m-%d")
    
    # Calculate spending from first day of month
    df_with_datetime = df.copy()
    df_with_datetime["timestamp"] = pd.to_datetime(df_with_datetime["timestamp"])
    monthly_spending_df = df_with_datetime[
        (df_with_datetime["sender_upi"] == user["upi_id"]) &
        (df_with_datetime["status"] == "SUCCESS") &
        (df_with_datetime["timestamp"] >= first_day_of_month)
    ]
    
    monthly_spending = monthly_spending_df["amount"].sum()
    month_name = today.strftime("%B %Y")
    
    st.markdown(f"""
    <div class="account-card" style="text-align: center; background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%); border: 2px solid #667eea;">
        <h2>💳 Monthly Spending Summary</h2>
        <h1 style="font-size: 2.5em; background: linear-gradient(135deg, #FF6B6B 0%, #FF8E72 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 1rem 0;">₹{monthly_spending:,.2f}</h1>
        <p style="font-size: 1.1em; color: #667eea;">Amount spent from <strong>{month_name}</strong></p>
    </div>
    """, unsafe_allow_html=True)
