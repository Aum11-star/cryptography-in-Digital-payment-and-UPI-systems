"""
pages/1_Login_Register.py — Authentication Page
================================================

Handles user registration and login. On registration:
  • SHA-256 password hash is stored (never plaintext)
  • RSA key pair is generated and stored for the user
  • UPI-style ID (e.g. alice@simpay) is assigned

On login:
  • Password is hashed and compared to the stored hash
  • Session state is updated with the full user record
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import register_user, authenticate_user, initialize_database

initialize_database()

st.set_page_config(page_title="Login / Register — SimPay", page_icon="👤", layout="centered")
st.title("👤 Login / Register")

# ── Session init ─────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

# If already logged in, show logout option
if st.session_state.user:
    user = st.session_state.user
    st.success(f"You are logged in as **{user['username']}** (`{user['upi_id']}`)")
    st.metric("Account Balance", f"₹{user['balance']:,.2f}")

    if st.button("🚪 Logout"):
        st.session_state.user = None
        st.rerun()
    st.stop()

# ── Tab selector ─────────────────────────────────────────────────────────────
tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

# =============================================================================
# REGISTER TAB
# =============================================================================
with tab_register:
    st.subheader("Create a new SimPay account")
    st.caption(
        "On registration, the system generates a 2048-bit RSA key pair for your account "
        "and assigns you a UPI-style payment ID."
    )

    with st.form("register_form"):
        reg_username = st.text_input("Username", placeholder="e.g. alice")
        reg_password = st.text_input("Password", type="password")
        reg_pin      = st.text_input("Transaction PIN (4–6 digits)", type="password", max_chars=6)
        reg_submit   = st.form_submit_button("Create Account", type="primary")

    if reg_submit:
        if not reg_username or not reg_password or not reg_pin:
            st.error("All fields are required.")
        elif not reg_pin.isdigit() or len(reg_pin) < 4:
            st.error("PIN must be 4–6 numeric digits.")
        else:
            with st.spinner("Generating RSA key pair and creating account..."):
                result = register_user(reg_username, reg_password, reg_pin)

            if result["success"]:
                st.success(result["message"])
                st.balloons()
                st.info("🔑 An RSA-2048 key pair has been generated for your account and stored securely.")
            else:
                st.error(result["message"])

# =============================================================================
# LOGIN TAB
# =============================================================================
with tab_login:
    st.subheader("Sign in to your SimPay account")

    with st.form("login_form"):
        log_username = st.text_input("Username")
        log_password = st.text_input("Password", type="password")
        log_submit   = st.form_submit_button("Login", type="primary")

    if log_submit:
        if not log_username or not log_password:
            st.error("Please enter username and password.")
        else:
            result = authenticate_user(log_username, log_password)
            if result["success"]:
                st.session_state.user = result["user"]
                st.success(f"Welcome back, {log_username}! Redirecting...")
                st.rerun()
            else:
                st.error(result["message"])

    st.divider()
    st.caption("**Security note:** Your password is never stored in plaintext. "
               "It is hashed with SHA-256 before being written to the database.")
