"""
app.py — SimPay: Secure Digital Payment Network Simulator
==========================================================

Entry point for the Streamlit application.
This is the Home / Welcome page. All other pages live in pages/.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import initialize_database, get_or_create_bank_keys

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="SimPay — Secure Payment Simulator",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Initialize DB and bank keys on first run ─────────────────────────────────
initialize_database()
bank_keys = get_or_create_bank_keys()

# ── Home page content ────────────────────────────────────────────────────────
st.title("🔐 SimPay — Secure Digital Payment Network Simulator")
st.caption("An academic demonstration of Hybrid Cryptography in a UPI-style payment network")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔑 RSA Key Exchange")
    st.write(
        "Each user and the bank server hold a 2048-bit RSA key pair. "
        "Transaction session keys are encrypted with the bank's public key."
    )

with col2:
    st.subheader("🛡️ AES-256 Encryption")
    st.write(
        "Transaction payloads (sender, receiver, amount, PIN) are encrypted "
        "with a fresh AES-256-CBC session key for every transaction."
    )

with col3:
    st.subheader("📊 Admin Analytics")
    st.write(
        "The Admin Dashboard loads the full ledger into Pandas, visualizes "
        "transaction volume, and flags anomalous transfers."
    )

st.divider()

st.subheader("Architecture Overview")
st.code("""
Sender Client                    Bank Server (SimPay Gateway)
─────────────────────            ────────────────────────────
 1. User enters payment details
 2. PIN hashed (SHA-256)
 3. Payload → AES-256-CBC ──── Encrypted Envelope ────►  4. RSA decrypt AES key
    (with random session key)                              5. AES decrypt payload
 4. AES key → RSA-OAEP ──────────────────────────────►  6. Validate PIN + Balance
    (with bank's public key)                              7. Update SQLite ledger
                                                          8. Return SUCCESS/FAIL
""", language="text")

st.info("👈 Use the sidebar to navigate. Start by registering an account on the **Login / Register** page.")

st.divider()

st.subheader("Bank Server RSA Public Key (Simulated Gateway)")
st.caption("All transaction payloads are encrypted to this key. Only the bank's private key can decrypt them.")
with st.expander("View Bank Public Key"):
    st.code(bank_keys["public_key"], language="text")
