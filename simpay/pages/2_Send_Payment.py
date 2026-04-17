"""
pages/2_Send_Payment.py — Initiate a Secure Payment
=====================================================

This page demonstrates the complete hybrid encryption pipeline:

    1. User fills in receiver UPI, amount, and PIN.
    2. PIN is hashed (SHA-256) locally.
    3. Payload dict is encrypted:
         a. A fresh 256-bit AES session key is generated.
         b. The payload is encrypted with AES-256-CBC.
         c. The AES key is encrypted with the bank's RSA public key.
    4. The encrypted envelope is "sent" to the simulated bank server.
    5. The bank server decrypts, validates, and settles the payment.
    6. Both the raw ciphertext AND the decrypted result are shown on screen
       to illustrate "Encryption in Transit."
"""

import streamlit as st
import sys, os, json, base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialize_database, get_or_create_bank_keys, get_user_by_upi
from crypto_utils import encrypt_transaction_payload, hash_pin
from bank_server import process_payment

initialize_database()

st.set_page_config(page_title="Send Payment — SimPay", page_icon="💸", layout="wide")
st.title("💸 Send Payment")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user" not in st.session_state or not st.session_state.user:
    st.warning("You must be logged in to send payments.")
    st.page_link("pages/1_Login_Register.py", label="Go to Login", icon="🔑")
    st.stop()

user = st.session_state.user

# Refresh user record from DB (balance may have changed)
fresh_user = get_user_by_upi(user["upi_id"])
if fresh_user:
    st.session_state.user = fresh_user
    user = fresh_user

# ── Layout ────────────────────────────────────────────────────────────────────
col_form, col_crypto = st.columns([1, 1], gap="large")

with col_form:
    st.subheader("Payment Details")
    st.metric("Your Balance", f"₹{user['balance']:,.2f}")
    st.caption(f"Your UPI ID: `{user['upi_id']}`")

    st.divider()

    with st.form("payment_form"):
        receiver_upi = st.text_input(
            "Receiver UPI ID",
            placeholder="e.g. bob@simpay",
            help="Enter the UPI ID of the person you want to pay."
        )
        amount = st.number_input(
            "Amount (₹)",
            min_value=1.0,
            max_value=float(user["balance"]),
            value=100.0,
            step=50.0
        )
        pin = st.text_input(
            "Transaction PIN",
            type="password",
            max_chars=6,
            help="Your 4–6 digit transaction PIN. It will be hashed before transmission."
        )
        submit = st.form_submit_button("🔐 Encrypt & Send", type="primary")

# ── Process payment when form is submitted ─────────────────────────────────
if submit:
    if not receiver_upi or not pin:
        st.error("All fields are required.")
        st.stop()

    bank_keys = get_or_create_bank_keys()
    bank_public_key = bank_keys["public_key"]

    # Build the raw payload
    payload = {
        "sender":   user["upi_id"],
        "receiver": receiver_upi.strip(),
        "amount":   amount,
        "pin_hash": hash_pin(pin)
    }

    with st.spinner("Encrypting payload and transmitting to bank server..."):
        # Encrypt the payload
        envelope = encrypt_transaction_payload(bank_public_key, payload)

        # Transmit to bank server (simulated)
        result = process_payment(envelope, user["upi_id"])

    # Refresh user balance
    fresh_user = get_user_by_upi(user["upi_id"])
    if fresh_user:
        st.session_state.user = fresh_user

    # ── Result banner ─────────────────────────────────────────────────────
    with col_form:
        if result["success"]:
            st.success(f"✅ {result['message']}")
            if result.get("is_anomalous"):
                st.warning("⚠️ This transaction has been flagged as anomalous (amount ≥ ₹5,000).")
        else:
            st.error(f"❌ Transaction Failed: {result['message']}")

    # ── Encryption in Transit Demo ────────────────────────────────────────
    with col_crypto:
        st.subheader("🔒 Encryption in Transit")
        st.caption("This panel demonstrates what the data looks like at each stage of the pipeline.")

        # --- Stage 1: Plaintext Payload ---
        with st.expander("📄 Stage 1: Plaintext Payload (before encryption)", expanded=True):
            display_payload = dict(payload)
            display_payload["pin_hash"] = payload["pin_hash"][:16] + "... [SHA-256]"
            st.json(display_payload)
            st.caption("This is the sensitive data that must be protected during transmission.")

        # --- Stage 2: AES-Encrypted Payload (Ciphertext) ---
        with st.expander("🔐 Stage 2: AES-256-CBC Encrypted Payload (Ciphertext)", expanded=True):
            st.text_area(
                "Ciphertext (Base64)",
                value=envelope["ciphertext_b64"],
                height=100,
                disabled=True,
                help="The transaction payload encrypted with a fresh AES-256 session key."
            )
            st.text_input(
                "IV (Initialization Vector, Base64)",
                value=envelope["iv_b64"],
                disabled=True,
                help="Random 16-byte value prepended to prevent identical ciphertexts for identical inputs."
            )
            st.caption("Without the AES key, this ciphertext is computationally indecipherable.")

        # --- Stage 3: RSA-Encrypted AES Key ---
        with st.expander("🗝️ Stage 3: RSA-OAEP Encrypted Session Key", expanded=True):
            st.text_area(
                "Encrypted AES Key (Base64)",
                value=envelope["encrypted_key_b64"],
                height=80,
                disabled=True,
                help="The AES session key, encrypted with the bank's RSA-2048 public key."
            )
            st.caption("Only the bank's private RSA key can recover the AES key — and therefore the payload.")

        # --- Stage 4: Bank Server Decryption Result ---
        if result.get("decrypted_payload"):
            with st.expander("🏦 Stage 4: Bank Server — Decrypted & Validated Payload", expanded=True):
                dp = dict(result["decrypted_payload"])
                dp["pin_hash"] = dp.get("pin_hash", "")[:16] + "... [verified]"
                st.json(dp)
                if result["success"]:
                    st.success("Bank server successfully decrypted, validated, and settled this transaction.")
                else:
                    st.error("Bank server decrypted the payload but validation failed.")

        # --- Full Envelope (raw) ---
        with st.expander("📦 Raw Encrypted Envelope (as transmitted)", expanded=False):
            st.json({
                "encrypted_key_b64": envelope["encrypted_key_b64"][:40] + "...",
                "iv_b64":            envelope["iv_b64"],
                "ciphertext_b64":    envelope["ciphertext_b64"][:40] + "..."
            })
            st.caption("This is the complete data structure transmitted from client to bank server.")

else:
    # Show static crypto explanation when no transaction is in progress
    with col_crypto:
        st.subheader("🔒 How Encryption Works")
        st.info(
            "When you click **Encrypt & Send**, the following happens:\n\n"
            "1. Your PIN is hashed with **SHA-256** locally — never sent in plaintext.\n"
            "2. A fresh **AES-256-CBC** session key is generated for this transaction only.\n"
            "3. The payload is encrypted with AES.\n"
            "4. The AES key is encrypted with the **bank's RSA-2048 public key**.\n"
            "5. The encrypted envelope is sent to the bank server.\n"
            "6. The bank decrypts using its private key, verifies your PIN and balance,\n"
            "   then updates the ledger.\n\n"
            "The ciphertext at each stage will appear here after you submit."
        )
        st.divider()
        st.subheader("Your RSA Public Key")
        st.caption("This key belongs to your SimPay account.")
        with st.expander("View Your Public Key"):
            st.code(user.get("public_key", ""), language="text")
