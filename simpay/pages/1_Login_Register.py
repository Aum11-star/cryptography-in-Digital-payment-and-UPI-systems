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
  • PIN verification required before viewing balance
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import register_user, authenticate_user, initialize_database, verify_user_pin
from ui_effects import inject_global_effects

initialize_database()

st.set_page_config(page_title="Login / Register — SimPay", page_icon="👤", layout="centered")
inject_global_effects()
st.markdown(
    """
<style>
    h1, h2, h3 { color: var(--simpay-text) !important; }
    .stButton > button {
        background: linear-gradient(135deg, #5f78ff 0%, #6a51c8 100%) !important;
        color: #fff !important;
        border: 0 !important;
        border-radius: 999px !important;
        box-shadow: 0 8px 20px rgba(88, 107, 220, 0.28) !important;
        transition: transform 0.22s ease, box-shadow 0.22s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 12px 28px rgba(88, 107, 220, 0.38) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px 12px 0 0 !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #5f78ff 0%, #6a51c8 100%) !important;
        color: white !important;
    }
    [data-testid="stForm"] {
        background: var(--simpay-card);
        border: 1px solid var(--simpay-border);
        border-radius: 14px;
        padding: 1rem;
    }
    .balance-card {
        background: linear-gradient(135deg, #5f78ff 0%, #6947be 52%, #2f91ff 100%);
        color: white;
        padding: 2.2rem;
        border-radius: 22px;
        box-shadow: 0 18px 40px rgba(69, 101, 224, 0.38);
        animation: simpay-pop 0.6s ease;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1 class='simpay-title'>🔐 SimPay — Secure Login</h1>", unsafe_allow_html=True)

# ── Session init ─────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None
if "pin_verified" not in st.session_state:
    st.session_state.pin_verified = False

# ── If logged in: show PIN verification screen ───────────────────────────────
if st.session_state.user and not st.session_state.pin_verified:
    user = st.session_state.user
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("")
    with col2:
        if st.button("🚪 Logout", key="logout_before_pin"):
            st.session_state.user = None
            st.session_state.pin_verified = False
            st.rerun()
    
    st.write(f"Welcome back, **{user['username']}**! 👋")
    st.write(f"Your UPI ID: `{user['upi_id']}`")
    
    st.divider()
    
    st.markdown("""
    <div style="text-align: center; padding: 1rem; border: 2px solid #667eea; border-radius: 15px; background: rgba(102, 126, 234, 0.05);">
        <h3>🔐 Enter Your Transaction PIN</h3>
        <p>Please enter your 4-6 digit PIN to view your balance securely.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("pin_verification"):
        pin_input = st.text_input("Transaction PIN", type="password", placeholder="••••")
        pin_submit = st.form_submit_button("Verify PIN", type="primary")
    
    if pin_submit:
        if verify_user_pin(user["upi_id"], pin_input):
            st.session_state.pin_verified = True
            st.success("✅ PIN verified successfully!")
            st.rerun()
        else:
            st.error("❌ Incorrect PIN. Please try again.")
    st.stop()

# ── If logged in and PIN verified: show balance and logout ───────────────────
if st.session_state.user and st.session_state.pin_verified:
    user = st.session_state.user
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.write("")
    with col2:
        st.markdown(f"""
        <div class="balance-card">
            <h2 style="color: white; -webkit-text-fill-color: unset; margin: 0;">💰 Account Balance</h2>
            <h1 style="font-size: 3em; color: #7dffcd; -webkit-text-fill-color: #7dffcd; margin: 1rem 0; font-weight: 900;">₹{user['balance']:,.2f}</h1>
            <p style="font-size: 1.2em; margin: 0; color: white;">Welcome, <strong>{user['username']}</strong></p>
            <p style="opacity: 0.9; color: white;">{user['upi_id']}</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.write("")
    
    st.divider()
    
    col_logout, col_space = st.columns([1, 4])
    with col_logout:
        if st.button("🚪 Logout"):
            st.session_state.user = None
            st.session_state.pin_verified = False
            st.rerun()
    
    st.info("👈 Use the sidebar to navigate to other pages.")
    st.stop()

# ── Tab selector ─────────────────────────────────────────────────────────────
tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

# =============================================================================
# REGISTER TAB
# =============================================================================
with tab_register:
    st.subheader("✨ Create a new SimPay account")
    st.caption(
        "On registration, the system generates a 2048-bit RSA key pair for your account "
        "and assigns you a UPI-style payment ID."
    )

    with st.form("register_form"):
        reg_username = st.text_input("👤 Username", placeholder="e.g. alice", key="reg_user")
        reg_password = st.text_input("🔐 Password", type="password", key="reg_pass")
        reg_pin      = st.text_input("📌 Transaction PIN (4–6 digits)", type="password", max_chars=6, key="reg_pin")
        
        reg_submit   = st.form_submit_button("✨ Create Account", type="primary", use_container_width=True)

    if reg_submit:
        if not reg_username or not reg_password or not reg_pin:
            st.error("❌ All fields are required.")
        elif not reg_pin.isdigit() or len(reg_pin) < 4:
            st.error("❌ PIN must be 4–6 numeric digits.")
        else:
            with st.spinner("🔄 Generating RSA key pair and creating account..."):
                result = register_user(reg_username, reg_password, reg_pin)

            if result["success"]:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); padding: 1.5rem; 
                            border-radius: 15px; text-align: center; border: 2px solid #84fab0;">
                    <h3 style="color: white; -webkit-background-clip: unset; -webkit-text-fill-color: unset;">
                        ✅ Congratulations! Your account is being successfully created.
                    </h3>
                </div>
                """, unsafe_allow_html=True)
                st.info("🔑 An RSA-2048 key pair has been generated for your account and stored securely.")
            else:
                st.error(f"❌ {result['message']}")

# =============================================================================
# LOGIN TAB
# =============================================================================
with tab_login:
    st.subheader("🔓 Sign in to your SimPay account")

    with st.form("login_form"):
        log_username = st.text_input("👤 Username", key="log_user")
        log_password = st.text_input("🔐 Password", type="password", key="log_pass")
        
        log_submit   = st.form_submit_button("🔓 Login", type="primary", use_container_width=True)

    if log_submit:
        if not log_username or not log_password:
            st.error("❌ Please enter username and password.")
        else:
            result = authenticate_user(log_username, log_password)
            if result["success"]:
                st.session_state.user = result["user"]
                st.session_state.pin_verified = False  # Reset PIN verification
                st.success(f"✅ Welcome back, {log_username}! Redirecting...")
                st.rerun()
            else:
                st.error(f"❌ {result['message']}")

    st.divider()
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); 
                padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea;">
        <strong>🔒 Security note:</strong> Your password is never stored in plaintext. 
        It is hashed with SHA-256 before being written to the database.
    </div>
    """, unsafe_allow_html=True)
