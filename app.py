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
    page_title="🛡️ Burnout Co-pilot",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_custom_styles()

# Hide Streamlit's component docs panel that appears in sidebar
st.markdown("""
<style>
section[data-testid="stSidebar"] iframe,
section[data-testid="stSidebar"] [data-testid="stHelpText"],
section[data-testid="stSidebar"] .stHelp,
div[class*="streamlit-expander"] iframe,
[data-testid="stSidebarUserContent"] > div > div > div[style*="overflow"],
section[data-testid="stSidebar"] > div > div > div > div[style*="height: 400px"],
section[data-testid="stSidebar"] > div > div > div > div[style*="overflow: auto"] {
    display: none !important;
    height: 0 !important;
    visibility: hidden !important;
}

/* ── Logout button — light lavender ─────────────────────────────────────── */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] button:focus,
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] div[data-testid="stButton"] button,
section[data-testid="stSidebar"] div.stButton > button,
section[data-testid="stSidebar"] div.stButton > button:focus {
    background-color: #e2e0ff !important;
    background-image: none !important;
    background: #e2e0ff !important;
    color: #2d3561 !important;
    border: 2px solid #a8a4ff !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.5px !important;
    box-shadow: 3px 3px 0px #c0bbff !important;
    padding: 0.4rem 1rem !important;
}
section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] .stButton button:hover,
section[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #cbc7ff !important;
    background: #cbc7ff !important;
    border-color: #7b76e0 !important;
    color: #1a1a3e !important;
    box-shadow: 4px 4px 0px #a8a4ff !important;
    transform: translateY(-1px) !important;
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


# ── Helper: always returns a non-empty display name ──────────────────────────
def _resolve_name(user_name: str, user_email: str) -> str:
    if user_name and user_name.strip():
        return user_name.strip()
    if user_email:
        return user_email.split("@")[0].replace(".", " ").title()
    return "User"


# ─────────────────────────────────────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_auth_page():
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px;">
            <div style="font-size:3.5rem;">🛡️</div>
            <div style="font-family:'Nunito',sans-serif;font-size:1.7rem;
                font-weight:900;color:#2d3561;">Burnout Co-pilot</div>
            <div style="font-size:0.88rem;color:#8892b0;margin-top:4px;">
                AI-based Digital Exhaustion Monitoring</div>
        </div>""", unsafe_allow_html=True)

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
            name  = st.text_input("Full name",        key="sn", placeholder="Anika Banerjee")
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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():
    uid          = st.session_state.user_uid
    user_email   = st.session_state.user_email
    user_name    = st.session_state.user_name

    # Always resolve to a real name — never empty
    display_name = _resolve_name(user_name, user_email)

    # Keep session state in sync (important for first login after old signup)
    if not st.session_state.user_name:
        st.session_state.user_name = display_name

    # NOTE: Streamlit does NOT start or stop the tracker anymore.
    # Architecture (finalized): Windows Startup -> startup_logger.py ->
    # tracker.py -> Supabase, running as ONE background process tied to
    # whichever credentials were saved via
    # `python startup_logger.py --save-credentials`. This dashboard is
    # purely a READ view onto that data.
    #
    # Why this changed: tracker.py uses module-level global state
    # (a single _tracker_thread, _key_times, etc. for the whole
    # process). Streamlit reruns the same script on every interaction
    # WITHOUT restarting the process, so if user A logged in first
    # (starting a tracker thread for A's uid) and user B logged in
    # afterward in the same running Streamlit process, `is_running()`
    # was already True, so `start_tracker(B_uid)` was silently skipped
    # — B's dashboard kept reading and saving A's tracker thread,
    # which is exactly why both accounts showed identical session
    # timings. Removing tracker control from the dashboard entirely
    # eliminates this whole class of bug.

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#a8a4ff22,#ff6b6b22);
            border-radius:16px;padding:16px;margin-bottom:16px;
            border:2px solid #e0e8ff;font-family:'Nunito',sans-serif;text-align:center;">
            <div style="font-size:2rem;">👤</div>
            <div style="font-weight:800;color:#2d3561;font-size:1.05rem;">{display_name}</div>
            <div style="font-size:0.76rem;color:#8892b0;">{user_email}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📡 Background Tracking Status**")
        st.caption("Tracked automatically by the Startup Logger, even when this dashboard is closed.")

        # Read the most recent session from Supabase instead of an
        # in-process buffer — there is no tracker running inside
        # Streamlit to read a live buffer FROM anymore (see note above).
        _recent = get_user_sessions(uid, limit=1)
        if _recent:
            last = _recent[-1]
            _ago_minutes = int((datetime.now().astimezone() - last["timestamp"]).total_seconds() // 60)
            _ago_str = f"{_ago_minutes} min ago" if _ago_minutes < 60 else f"{_ago_minutes // 60}h {_ago_minutes % 60}m ago"

            st.markdown(f"""
            <div style="background:white;border:2px solid #e0e8ff;border-radius:14px;
                padding:14px;font-family:'Nunito',sans-serif;box-shadow:4px 4px 0px #c8d0f0;">
                <div style="font-size:0.78rem;color:#8892b0;margin-bottom:8px;font-weight:700;
                    text-transform:uppercase;letter-spacing:0.5px;">Last Synced Session</div>
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span style="color:#2d3561;font-size:0.85rem;">⌨️ Typing Speed</span>
                    <span style="color:#a8a4ff;font-weight:800;">{last["typing_mean"]} kpm</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span style="color:#2d3561;font-size:0.85rem;">🔀 App Switches</span>
                    <span style="color:#a8a4ff;font-weight:800;">{last["task_switching"]}</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span style="color:#2d3561;font-size:0.85rem;">🕐 Synced</span>
                    <span style="color:#a8a4ff;font-weight:800;">{_ago_str}</span>
                </div>
                <div style="display:flex;justify-content:space-between;">
                    <span style="color:#2d3561;font-size:0.85rem;">🌙 Late Night</span>
                    <span style="color:{"#ff4b4b" if last["late_night"] else "#00c48c"};font-weight:800;">
                        {"Yes ⚠️" if last["late_night"] else "No ✅"}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No sessions synced yet. Make sure the Startup Logger is running in the background.")

        st.caption("💾 New sessions sync automatically — refresh to see the latest.")
        st.markdown("---")

        # Re-inject right here so it fires AFTER Streamlit's own stylesheet loads
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] button,
        section[data-testid="stSidebar"] .stButton > button {
            background-color: #e2e0ff !important;
            background:       #e2e0ff !important;
            color:            #2d3561 !important;
            border:           2px solid #a8a4ff !important;
            border-radius:    12px !important;
            font-weight:      800 !important;
            box-shadow:       3px 3px 0px #c0bbff !important;
        }
        section[data-testid="stSidebar"] button:hover,
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #cbc7ff !important;
            background:       #cbc7ff !important;
            border-color:     #7b76e0 !important;
            color:            #1a1a3e !important;
            box-shadow:       4px 4px 0px #a8a4ff !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

    st.set_page_config(
    page_title="Burnout Copilot",
    initial_sidebar_state="collapsed"
)

    # ── LOAD DATA ─────────────────────────────────────────────────────────────
    sessions = get_user_sessions(uid, limit=200)

    if not sessions:
        st.title(f"🛡️ Welcome, {display_name}!")
        st.markdown("""
        <div style="background:rgba(168,164,255,0.1);border:2px solid #a8a4ff;
            border-radius:20px;padding:36px;text-align:center;
            font-family:'Nunito',sans-serif;">
            <div style="font-size:3rem;">📊</div>
            <div style="font-size:1.3rem;font-weight:800;color:#2d3561;margin-bottom:10px;">
                No sessions yet</div>
            <div style="color:#8892b0;font-size:0.92rem;line-height:1.8;">
                The background tracker is running and will collect your data every
                <strong>1 hour</strong> automatically.<br>
                Or use <strong>Log Manual Session</strong> in the sidebar to add data now.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── BUILD DATAFRAME ───────────────────────────────────────────────────────
    df = pd.DataFrame(sessions)
    # NOTE: get_user_sessions() already converts each timestamp to local
    # system time (see supabase_manager.py). Do NOT pass utc=True here —
    # that would force everything back to UTC and undo the conversion,
    # which is exactly the bug that showed 7 AM instead of 1 PM.
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["session_index"] = range(len(df))

    for col in ["typing_mean", "typing_variance", "task_switching",
                "work_duration", "late_night", "hour_of_day"]:
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

    # ── TITLE ────────────────────────────────────────────────────────────────
    st.title(f"🛡️ {display_name}'s Burnout Dashboard")

    # ── WELLNESS CARDS ────────────────────────────────────────────────────────
    late_n   = int(df["late_night"].sum())
    rest_pct = round((1 - df["late_night"].mean()) * 100)
    max_var  = max(df["typing_variance"].max(), 1)
    foc_pct  = round((1 - df["typing_variance"].mean() / max_var) * 100)
    avg_dur  = df["work_duration"].mean()
    bal_pct  = round(max(0, (1 - abs(avg_dur - 8) / 8)) * 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("😴 Rest Quality",     f"{rest_pct}%", delta=f"{late_n} late night sessions", delta_color="off")
    c2.metric("⚡ Focus Level",       f"{foc_pct}%",  delta=f"{len(df)} sessions recorded",  delta_color="off")
    c3.metric("⏱️ Work-Life Balance", f"{bal_pct}%",  delta=f"avg {avg_dur:.1f} hrs/day",    delta_color="off")

    # ── GAUGE + FORECAST ──────────────────────────────────────────────────────
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("Real-time Burnout Risk")
        st.plotly_chart(create_burnout_gauge(current_cli), use_container_width=True)

    with r2:
        st.subheader("7-Day Burnout Forecast")
        fdf   = get_7_day_forecast(current_cli)
        dates = fdf["Date"].tolist()
        ff    = go.Figure()
        for y_top, y_bot, col in [(0.4, 0.0, "rgba(0,204,150,0.10)"),
                                   (0.7, 0.4, "rgba(255,161,90,0.10)"),
                                   (1.0, 0.7, "rgba(239,85,59,0.10)")]:
            ff.add_trace(go.Scatter(
                x=dates + dates[::-1],
                y=[y_top] * 7 + [y_bot] * 7,
                fill="toself", fillcolor=col,
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip", showlegend=False))
        ff.add_trace(go.Scatter(
            x=dates, y=fdf["CLI"],
            mode="lines+markers",
            line=dict(color="#a8a4ff", width=3),
            marker=dict(color="white", size=9, line=dict(color="#a8a4ff", width=3)),
            hovertemplate="<b>%{x|%a %b %d}</b><br>CLI: <b>%{y:.3f}</b><extra></extra>",
            showlegend=False))
        ff.add_hline(y=0.4, line_dash="dot", line_color="rgba(0,204,150,0.6)",
                     annotation_text="Low/Medium",
                     annotation_font=dict(color="#00cc96", size=10))
        ff.add_hline(y=0.7, line_dash="dot", line_color="rgba(239,85,59,0.6)",
                     annotation_text="Medium/High",
                     annotation_font=dict(color="#ef553b", size=10))
        ff.update_layout(
            height=350, margin=dict(l=10, r=60, t=20, b=10),
            paper_bgcolor="white", plot_bgcolor="#f8f9ff",
            font=dict(color="#2d3561", family="Nunito"),
            xaxis=dict(gridcolor="#eceef8", color="#2d3561", tickformat="%b %d",
                       tickfont=dict(size=11, color="#2d3561")),
            yaxis=dict(gridcolor="#eceef8", color="#2d3561", range=[0, 1.05],
                       tickformat=".1f", tickfont=dict(size=11, color="#2d3561")),
            hoverlabel=dict(bgcolor="white", bordercolor="#a8a4ff",
                            font=dict(color="#2d3561", size=12)),
            showlegend=False)
        st.plotly_chart(ff, use_container_width=True)

    # ── TREND CHART ───────────────────────────────────────────────────────────
    st.subheader(f"{display_name}'s Burnout Trend")
    st.caption("💡 Hover over any point to see what drove the score that day.")
    st.plotly_chart(create_burnout_trend_chart(df, display_name), use_container_width=True)

    # ── SUGGESTIONS ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 💡 Personalised Suggestions for {display_name}")
    st.caption("Based on your latest recorded session.")
    sugs = get_suggestions(
        cli=current_cli,
        typing_mean=float(latest.get("typing_mean", 0)),
        typing_variance=float(latest.get("typing_variance", 0)),
        task_switching=int(latest.get("task_switching", 0)),
        work_duration=float(latest.get("work_duration", 0)),
        late_night=int(latest.get("late_night", 0)),
        user_name=display_name,
    )
    st.markdown(get_suggestion_cards_html(sugs), unsafe_allow_html=True)

    # ── EXPLAINABILITY ────────────────────────────────────────────────────────
    if model and len(df) >= 3:
        user_row = df.tail(1).copy().reset_index(drop=True)
        if "hour_of_day" not in user_row.columns:
            user_row["hour_of_day"] = datetime.now().hour
        render_explainability_panel(
            model=model, user_row=user_row,
            df_full=df, user_id=uid, user_name=display_name)

    # ── RAW DATA TABLE ────────────────────────────────────────────────────────
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