# src/ui/styles.py

import streamlit as st


def apply_custom_styles():
    css = """
    <style>
    /* ── GOOGLE FONTS ──────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Nunito:wght@400;600;700;800;900&display=swap');

    /* ── CSS VARIABLES ─────────────────────────────────────────────────────── */
    :root {
        --bg-gradient: linear-gradient(135deg, #eef2ff 0%, #fdf2f8 45%, #f5f3ff 100%);
        --card-bg: rgba(255, 255, 255, 0.88);
        --card-border: 1.5px solid rgba(230, 234, 250, 0.9);
        --card-shadow: 0 10px 30px -5px rgba(130, 140, 200, 0.12), 0 4px 10px -2px rgba(130, 140, 200, 0.06);
        --card-radius: 24px;
        --card-radius-sm: 16px;
        
        --text-main: #1e1b4b;
        --text-muted: #828ba0;
        
        --primary-gradient: linear-gradient(90deg, #8b5cf6 0%, #ec4899 100%);
        --primary-hover: linear-gradient(90deg, #7c3aed 0%, #db2777 100%);
        --primary-shadow: 0 8px 20px -3px rgba(236, 72, 153, 0.35);
        
        --accent-purple: #8b5cf6;
        --accent-pink: #ec4899;
        --accent-cyan: #06b6d4;
        --accent-green: #10b981;
    }

    /* ── GLOBAL APP BACKGROUND ─────────────────────────────────────────────── */
    .stApp {
        background: var(--bg-gradient) !important;
        font-family: 'Plus Jakarta Sans', 'Nunito', sans-serif !important;
        color: var(--text-main) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px !important;
    }

    /* ── HEADINGS ──────────────────────────────────────────────────────────── */
    h1, h2, h3, h4 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800 !important;
        color: var(--text-main) !important;
        letter-spacing: -0.4px !important;
    }

    /* ── SIDEBAR ───────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(16px) !important;
        border-right: 1.5px solid rgba(230, 234, 250, 0.8) !important;
        box-shadow: 6px 0 25px rgba(140, 150, 210, 0.08) !important;
        min-width: 270px !important;
        max-width: 270px !important;
    }

    /* ── INPUT FIELDS (Text / Password) ────────────────────────────────────── */
    .stTextInput input {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 14px !important;
        color: var(--text-main) !important;
        padding: 12px 16px !important;
        font-size: 0.92rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02) !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.15) !important;
    }

    /* ── PRIMARY & SECONDARY BUTTONS ───────────────────────────────────────── */
    button[kind="primary"], .stButton > button[kind="primary"] {
        background: var(--primary-gradient) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.65rem 1.2rem !important;
        box-shadow: var(--primary-shadow) !important;
        transition: all 0.25s ease !important;
    }
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
        background: var(--primary-hover) !important;
        box-shadow: 0 10px 24px -2px rgba(236, 72, 153, 0.45) !important;
        transform: translateY(-1px) !important;
    }

    button[kind="secondary"], .stButton > button {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover, .stButton > button:hover {
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
        color: #1e293b !important;
        transform: translateY(-1px) !important;
    }

    /* ── TABS ──────────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px !important;
        background-color: transparent !important;
        border-bottom: 1.5px solid #eef2f6 !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 16px !important;
        font-weight: 700 !important;
        color: var(--text-muted) !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ec4899 !important;
        border-bottom: 2.5px solid #ec4899 !important;
    }

    /* ── METRIC CARDS ──────────────────────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: var(--card-bg) !important;
        border-radius: var(--card-radius) !important;
        border: var(--card-border) !important;
        box-shadow: var(--card-shadow) !important;
        backdrop-filter: blur(12px) !important;
        padding: 22px 24px !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 16px 36px -6px rgba(130, 140, 200, 0.16) !important;
    }
    div[data-testid="stMetric"] label {
        color: var(--text-muted) !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        text-transform: capitalize !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text-main) !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }

    /* ── PLOTLY CONTAINERS ─────────────────────────────────────────────────── */
    div[data-testid="stPlotlyChart"] {
        background: var(--card-bg) !important;
        border-radius: var(--card-radius) !important;
        border: var(--card-border) !important;
        box-shadow: var(--card-shadow) !important;
        padding: 12px !important;
        backdrop-filter: blur(12px) !important;
    }

    /* ── CLEAN SCROLLBAR ───────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)