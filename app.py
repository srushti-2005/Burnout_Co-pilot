# app.py

import streamlit as st
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

from src.auth.supabase_client    import init_supabase
from src.auth.auth_manager       import login, signup, logout, reset_password
from src.data.supabase_manager   import get_user_sessions, save_session
from src.suggestions.suggestion_engine import get_suggestions, get_suggestion_cards_html

from src.cli_logic      import (
    normalize_with_fixed_bounds, calculate_cli, categorize_cli,
    get_training_weights, get_training_bounds,
)
from src.ui.components  import (
    create_burnout_gauge, create_burnout_trend_chart, render_explainability_panel
)
from src.forecaster     import get_7_day_forecast
from src.ui.styles      import apply_custom_styles
from src.config.config  import MODEL_PATH
import plotly.graph_objects as go

st.set_page_config(
    page_title="Burnout Copilot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_custom_styles()

# ── Sidebar & Navigation Cleanup ─────────────────────────────────────────────
st.markdown("""
<style>
section[data-testid="stSidebar"] iframe,
section[data-testid="stSidebar"] [data-testid="stHelpText"],
section[data-testid="stSidebar"] .stHelp {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def _init_backend():
    return init_supabase()
_init_backend()

@st.cache_resource
def load_model():
    try:    return joblib.load(MODEL_PATH)
    except: return None
model = load_model()

for k, v in {"logged_in": False, "user_uid": None, "user_email": None, "user_name": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _resolve_name(user_name: str, user_email: str) -> str:
    if user_name and user_name.strip():
        return user_name.strip()
    if user_email:
        return user_email.split("@")[0].replace(".", " ").title()
    return "User"


# ─────────────────────────────────────────────────────────────────────────────
# DREAM UI: AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_auth_page():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="text-align: center; margin-top: 40px; margin-bottom: 24px;">
            <div style="font-size: 3.2rem; filter: drop-shadow(0 8px 16px rgba(139, 92, 246, 0.3));">🧠</div>
            <div style="font-size: 1.9rem; font-weight: 800; color: #1e1b4b; margin-top: 6px; letter-spacing: -0.5px;">
                Burnout Copilot
            </div>
            <div style="font-size: 0.88rem; color: #64748b; margin-top: 4px; font-weight: 500;">
                AI-powered wellness insights • Live & continuous
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_l, tab_s = st.tabs(["🔑 Login", "✨ Sign Up"])

        with tab_l:
            st.markdown("<br>", unsafe_allow_html=True)
            email = st.text_input("Email", key="le", placeholder="you@example.com")
            pwd   = st.text_input("Password", type="password", key="lp", placeholder="••••••••")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Login", use_container_width=True, type="primary"):
                    if not email or not pwd:
                        st.error("Enter email and password.")
                    else:
                        with st.spinner("Logging in..."):
                            r = login(email.strip(), pwd)
                        if r["success"]:
                            st.session_state.update(
                                logged_in=True,
                                user_uid=r["uid"],
                                user_email=r["email"],
                                user_name=r.get("display_name", ""),
                            )
                            st.rerun()
                        else:
                            st.error(r["error"])
            with c2:
                if st.button("Forgot password?", use_container_width=True):
                    if email:
                        r = reset_password(email.strip())
                        st.success("Reset email sent!") if r["success"] else st.error(r.get("error"))
                    else:
                        st.warning("Enter your email first.")

        with tab_s:
            st.markdown("<br>", unsafe_allow_html=True)
            name  = st.text_input("Full name",        key="sn", placeholder="Alex Doe")
            seml  = st.text_input("Email",            key="se", placeholder="you@example.com")
            sp1   = st.text_input("Password",         key="sp1", type="password", placeholder="min 6 chars")
            sp2   = st.text_input("Confirm password", key="sp2", type="password", placeholder="••••••••")
            if st.button("Create Account", use_container_width=True, type="primary"):
                if not all([name, seml, sp1, sp2]):
                    st.error("Fill in all fields.")
                elif sp1 != sp2:
                    st.error("Passwords do not match.")
                elif len(sp1) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        r = signup(seml.strip(), sp1, name.strip())
                    if r["success"]:
                        st.session_state.update(
                            logged_in=True,
                            user_uid=r["uid"],
                            user_email=r["email"],
                            user_name=r["display_name"],
                        )
                        st.rerun()
                    else:
                        st.error(r["error"])

        st.markdown("""
        <div style="text-align: center; margin-top: 50px; color: #828ba0; font-size: 0.8rem; font-weight: 500;">
            ✦ Burnout Copilot AI &nbsp;|&nbsp; Always here to help you thrive
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DREAM UI: MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():
    uid          = st.session_state.user_uid
    user_email   = st.session_state.user_email
    user_name    = st.session_state.user_name
    display_name = _resolve_name(user_name, user_email)

    if not st.session_state.user_name:
        st.session_state.user_name = display_name

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <div style="font-size: 1.8rem;">🧠</div>
            <div>
                <div style="font-weight: 800; font-size: 1.1rem; color: #1e1b4b; line-height: 1.2;">Burnout<br>Copilot ✦</div>
            </div>
        </div>

        <div style="
            background: rgba(16, 185, 129, 0.1);
            color: #059669;
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 0.78rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 20px;
        ">
            <span style="height: 7px; width: 7px; background: #10b981; border-radius: 50%; display: inline-block;"></span>
            Live Tracking Active
        </div>

        <div style="
            background: rgba(255, 255, 255, 0.85);
            border: 1.5px solid #eef2f6;
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        ">
            <div style="
                background: linear-gradient(135deg, #8b5cf6, #ec4899);
                border-radius: 50%;
                width: 38px;
                height: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 700;
                font-size: 0.95rem;
            ">{display_name[0].upper()}</div>
            <div>
                <div style="font-weight: 700; color: #1e1b4b; font-size: 0.92rem;">{display_name}</div>
                <div style="font-size: 0.72rem; color: #828ba0;">{user_email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        _recent = get_user_sessions(uid, limit=1)
        if _recent:
            last = _recent[-1]
            _ago_minutes = int((datetime.now().astimezone() - last["timestamp"]).total_seconds() // 60)
            _ago_str = f"{_ago_minutes} min ago" if _ago_minutes < 60 else f"{_ago_minutes // 60}h {_ago_minutes % 60}m ago"

            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.7); border: 1.5px solid #eef2f6; border-radius: 16px; padding: 12px; font-size: 0.8rem;">
                <div style="color: #828ba0; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; margin-bottom: 6px;">Live Sync Pulse</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #64748b;">Typing Speed</span>
                    <span style="color: #8b5cf6; font-weight: 700;">{last["typing_mean"]} kpm</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #64748b;">App Switches</span>
                    <span style="color: #8b5cf6; font-weight: 700;">{last["task_switching"]}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #64748b;">Synced</span>
                    <span style="color: #8b5cf6; font-weight: 700;">{_ago_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

        # Copilot Widget Placeholder
        st.markdown("""
        <div style="margin-top: 40px; display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 2.2rem;">🤖</div>
            <div style="background: white; border: 1.5px solid #e2e8f0; border-radius: 14px; padding: 6px 12px; font-size: 0.75rem; font-weight: 600; color: #8b5cf6; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                I'm here for you! 💜
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── LOAD DATA ─────────────────────────────────────────────────────────────
    sessions = get_user_sessions(uid, limit=200)

    if not sessions:
        st.title(f"🧠 Welcome, {display_name}!")
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.85); border: 1.5px solid #eef2f6; border-radius: 24px; padding: 40px; text-align: center; box-shadow: 0 10px 30px rgba(130, 140, 200, 0.08);">
            <div style="font-size: 3rem; margin-bottom: 10px;">📊</div>
            <h3 style="margin-bottom: 6px;">No sessions synced yet</h3>
            <p style="color: #828ba0; font-size: 0.9rem;">The background tracker is actively monitoring and will log your activity automatically.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── DATAFRAME COMPUTATION ─────────────────────────────────────────────────
    df = pd.DataFrame(sessions)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["session_index"] = range(len(df))

    for col in ["typing_mean", "typing_variance", "task_switching", "work_duration", "late_night", "hour_of_day"]:
        if col not in df.columns:
            df[col] = 0

    weights = get_training_weights()
    bounds  = get_training_bounds()
    df_norm = normalize_with_fixed_bounds(df, bounds)
    df_norm["CLI"]          = df_norm.apply(lambda row: calculate_cli(row, weights), axis=1)
    df_norm["CLI_category"] = df_norm["CLI"].apply(categorize_cli)
    df = df_norm.copy()
    df["user_id"] = df.get("uid", uid)

    latest      = df.iloc[-1]
    current_cli = float(latest["CLI"])

    # ── DASHBOARD HEADER ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 2.1rem; margin: 0 0 4px 0;">{display_name}'s Burnout Copilot 👋</h1>
        <p style="color: #828ba0; font-size: 0.9rem; margin: 0;">AI-powered wellness insights • Live & continuous</p>
    </div>
    """, unsafe_allow_html=True)

    # ── METRIC CARDS ──────────────────────────────────────────────────────────
    late_n   = int(df["late_night"].sum())
    rest_pct = round((1 - df["late_night"].mean()) * 100)
    max_var  = max(df["typing_variance"].max(), 1)
    foc_pct  = round((1 - df["typing_variance"].mean() / max_var) * 100)
    avg_dur  = df["work_duration"].mean()
    bal_pct  = round(max(0, (1 - abs(avg_dur - 8) / 8)) * 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("🌙 Rest Quality",     f"{rest_pct}%", delta=f"{late_n} late night sessions", delta_color="off")
    c2.metric("🧠 Focus Score",      f"{foc_pct}%",  delta=f"{len(df)} sessions recorded",  delta_color="off")
    c3.metric("❤️ Work-Life Balance", f"{bal_pct}%",  delta=f"avg {avg_dur:.1f} hrs/day",    delta_color="off")

    # ── GAUGE + FORECAST ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("Real-time Burnout Risk")
        st.plotly_chart(create_burnout_gauge(current_cli), use_container_width=True)

    with r2:
        st.subheader("7-Day Burnout Forecast")
        fdf   = get_7_day_forecast(current_cli)
        dates = fdf["Date"].tolist()
        ff    = go.Figure()
        ff.add_trace(go.Scatter(
            x=dates, y=fdf["CLI"],
            mode="lines+markers",
            line=dict(color="#8b5cf6", width=3, shape='spline'),
            marker=dict(color="#ec4899", size=8, line=dict(color="white", width=2)),
            fill='tozeroy',
            fillcolor='rgba(139, 92, 246, 0.08)',
            hovertemplate="<b>%{x|%a %b %d}</b><br>CLI: <b>%{y:.3f}</b><extra></extra>",
            showlegend=False))
        ff.add_hline(y=0.4, line_dash="dash", line_color="rgba(16, 185, 129, 0.4)",
                     annotation_text="Low", annotation_font=dict(color="#10b981", size=10))
        ff.add_hline(y=0.7, line_dash="dash", line_color="rgba(239, 68, 68, 0.4)",
                     annotation_text="High", annotation_font=dict(color="#ef4444", size=10))
        ff.update_layout(
            height=320, margin=dict(l=10, r=30, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#1e1b4b", family="Plus Jakarta Sans"),
            xaxis=dict(gridcolor="#f1f5f9", color="#64748b", tickformat="%b %d"),
            yaxis=dict(gridcolor="#f1f5f9", color="#64748b", range=[0, 1.05]),
            hoverlabel=dict(bgcolor="white", bordercolor="#8b5cf6", font=dict(color="#1e1b4b", size=12)),
            showlegend=False)
        st.plotly_chart(ff, use_container_width=True)

    # ── TREND CHART ───────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"{display_name}'s Burnout Trend")
    st.plotly_chart(create_burnout_trend_chart(df, display_name), use_container_width=True)

    # ── SUGGESTIONS & EXPLAINABILITY ──────────────────────────────────────────
    if model and len(df) >= 3:
        user_row = df.tail(1).copy().reset_index(drop=True)
        if "hour_of_day" not in user_row.columns:
            user_row["hour_of_day"] = datetime.now().hour
        render_explainability_panel(
            model=model, user_row=user_row,
            df_full=df, user_id=uid, user_name=display_name)

    # ── RAW DATA TABLE ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(f"📋 View All of {display_name}'s Sessions"):
        disp = df[["timestamp", "typing_mean", "typing_variance",
                   "task_switching", "work_duration", "late_night",
                   "CLI", "CLI_category"]].copy()
        disp["late_night"] = disp["late_night"].map({0: "No", 1: "Yes"})
        disp["timestamp"]  = disp["timestamp"].dt.strftime("%d %b %Y  %H:%M")
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ── ROUTER ────────────────────────────────────────────────────────────────────
if st.session_state.logged_in:
    show_dashboard()
else:
    show_auth_page()