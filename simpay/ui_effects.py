import streamlit as st


def inject_global_effects() -> None:
    """Inject shared visual effects for all pages."""
    st.markdown(
        """
<style>
    :root {
        --simpay-text: #1f2a44;
        --simpay-card: rgba(255, 255, 255, 0.84);
        --simpay-border: rgba(84, 112, 226, 0.35);
        --simpay-glow: rgba(83, 139, 255, 0.16);
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 8% 15%, rgba(80, 145, 255, 0.17), transparent 26%),
            radial-gradient(circle at 90% 8%, rgba(130, 90, 255, 0.14), transparent 30%),
            radial-gradient(circle at 72% 86%, rgba(91, 182, 255, 0.17), transparent 28%),
            linear-gradient(145deg, #f8fbff 0%, #eff4ff 38%, #f9f4ff 100%);
        background-attachment: fixed;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #dbe8ff 0%, #c4d9ff 100%) !important;
        border-right: 1px solid rgba(78, 118, 220, 0.25) !important;
    }

    [data-testid="stSidebar"] * {
        color: #153069 !important;
    }

    [data-testid="stSidebarNav"] a {
        border-radius: 10px;
    }

    [data-testid="stSidebarNav"] a:hover {
        background: rgba(84, 124, 230, 0.15) !important;
    }

    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: rgba(84, 124, 230, 0.24) !important;
        color: #0f2f7f !important;
    }

    .simpay-glass {
        background: var(--simpay-card);
        border: 1px solid var(--simpay-border);
        border-radius: 16px;
        box-shadow: 0 12px 28px rgba(52, 82, 172, 0.14);
        backdrop-filter: blur(8px);
    }

    .simpay-float {
        animation: simpay-float 4.8s ease-in-out infinite;
    }

    @keyframes simpay-float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }

    .simpay-pop {
        animation: simpay-pop 0.55s ease;
    }

    @keyframes simpay-pop {
        from { opacity: 0; transform: translateY(12px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }

    .simpay-title {
        background: linear-gradient(135deg, #5f78ff 0%, #6a51c8 48%, #2c9dff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
    }
</style>
""",
        unsafe_allow_html=True,
    )
