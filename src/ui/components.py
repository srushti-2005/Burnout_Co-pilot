# src/ui/components.py

import plotly.graph_objects as go
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# Burnout Gauge — unchanged
# ═══════════════════════════════════════════════════════════════════════════════

def create_burnout_gauge(score, title="Burnout Risk Level"):
    """
    Renders the burnout gauge using Plotly's NATIVE indicator bar +
    a dynamic threshold marker as the needle, instead of a hand-drawn
    line.

    HISTORY:
    1. Original version hid Plotly's built-in bar and drew a custom
       needle using manual trigonometry (add_shape). That math had an
       offset bug — at score=0 the needle should point due left, but
       landed near "20" instead, disagreeing with the "0%" number next
       to it.
    2. Fixed by switching to Plotly's native 'bar', which is always
       internally consistent with the number (both come from the same
       `value`). But the bar is a FILLED ARC FROM 0 TO VALUE — at
       score=0 (or very close to it) that arc has ~zero length, so it
       becomes invisible. That's why "the needle disappeared" for very
       low scores.
    3. Fixed here: added a 'threshold' marker whose value is the exact
       CURRENT score, not a fixed reference point. Plotly always draws
       a threshold as a crisp line AT that position, regardless of how
       long the bar itself is — so it's visible even at exactly 0%,
       sitting right at the leftmost tick. The colored zones
       (green/orange/red) already communicate the "danger zone" a
       static threshold used to mark, so nothing is lost by making it
       dynamic instead of fixed at 80.
    """
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0

    score      = max(0, min(score, 1))
    percentage = score * 100

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        number={'suffix': "%", 'font': {'size': 38}},
        title={'text': title, 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#1a1a2e", 'thickness': 0.25},  # filled progress arc
            'steps': [
                {'range': [0,   40],  'color': "#00cc96"},
                {'range': [40,  75],  'color': "#ffa15a"},
                {'range': [75, 100],  'color': "#ef553b"},
            ],
            'threshold': {
                'line': {'color': "#ff0055", 'width': 5},
                'thickness': 0.9,
                'value': percentage,   # DYNAMIC — the actual needle, always visible
            }
        }
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#2d3561", family="Nunito"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Burnout Trend Chart — accepts name string for title
# ═══════════════════════════════════════════════════════════════════════════════

def create_burnout_trend_chart(user_df: pd.DataFrame, user_label):
    """
    Interactive Plotly trend chart.
    user_label : str (name) or int (id) — used only for chart title.

    Hover tooltip shows:
      Date · CLI Score · Risk Level · Top Driver · raw feature values
    """

    df = user_df.copy().reset_index(drop=True)

    def risk_label(cli):
        if   cli < 0.4: return "🟢 Low"
        elif cli < 0.7: return "🟡 Medium"
        else:           return "🔴 High"

    def top_driver(row):
        candidates = {}
        if "typing_variance" in row.index: candidates["Typing Variance"] = float(row["typing_variance"])
        if "task_switching"  in row.index: candidates["Task Switching"]  = float(row["task_switching"])
        if "work_duration"   in row.index: candidates["Work Duration"]   = float(row["work_duration"])
        if "late_night"      in row.index: candidates["Late Night Work"] = float(row["late_night"]) * 10
        return max(candidates, key=candidates.get) if candidates else "N/A"

    df["risk_label"] = df["CLI"].apply(risk_label)
    df["top_driver"] = df.apply(top_driver, axis=1)
    color_map        = {"🟢 Low": "#00cc96", "🟡 Medium": "#ffa15a", "🔴 High": "#ef553b"}
    df["pt_color"]   = df["risk_label"].map(color_map)

    def make_hover(r):
        ts   = str(r.get("timestamp", ""))[:16]
        tv   = r.get("task_switching",  "N/A")
        wd   = r.get("work_duration",   "N/A")
        tvar = r.get("typing_variance", "N/A")
        ln   = "Yes" if r.get("late_night", 0) == 1 else "No"
        return (
            f"<b>📅 Date:</b> {ts}<br>"
            f"<b>📊 CLI Score:</b> {r['CLI']:.3f}<br>"
            f"<b>⚠️ Risk Level:</b> {r['risk_label']}<br>"
            f"──────────────────<br>"
            f"<b>🔺 Top Driver:</b> {r['top_driver']}<br>"
            f"<b>Task Switching:</b> {tv}<br>"
            f"<b>Work Duration:</b> {wd} hrs<br>"
            f"<b>Typing Variance:</b> {tvar}<br>"
            f"<b>Late Night Work:</b> {ln}"
        )

    df["hover"] = df.apply(make_hover, axis=1)

    ts_list   = list(df["timestamp"])
    ts_rev    = ts_list[::-1]

    low_band  = go.Scatter(x=ts_list+ts_rev, y=[0.0]*len(df)+[0.4]*len(df),
                           fill="toself", fillcolor="rgba(0,204,150,0.07)",
                           line=dict(color="rgba(0,0,0,0)"), name="Low Zone",    hoverinfo="skip")
    med_band  = go.Scatter(x=ts_list+ts_rev, y=[0.4]*len(df)+[0.7]*len(df),
                           fill="toself", fillcolor="rgba(255,161,90,0.07)",
                           line=dict(color="rgba(0,0,0,0)"), name="Medium Zone", hoverinfo="skip")
    high_band = go.Scatter(x=ts_list+ts_rev, y=[0.7]*len(df)+[1.0]*len(df),
                           fill="toself", fillcolor="rgba(239,85,59,0.07)",
                           line=dict(color="rgba(0,0,0,0)"), name="High Zone",   hoverinfo="skip")

    line_trace = go.Scatter(
        x=df["timestamp"], y=df["CLI"],
        mode="lines+markers", name="CLI Score",
        line=dict(color="#5DA5F5", width=2),
        marker=dict(color=df["pt_color"], size=9, line=dict(color="white", width=1)),
        hovertext=df["hover"], hovertemplate="%{hovertext}<extra></extra>",
    )

    fig = go.Figure(data=[low_band, med_band, high_band, line_trace])

    fig.add_hline(y=0.4, line_dash="dot", line_color="rgba(255,161,90,0.45)",
                  annotation_text="Medium threshold", annotation_position="bottom right",
                  annotation_font_color="#ffa15a")
    fig.add_hline(y=0.7, line_dash="dot", line_color="rgba(239,85,59,0.45)",
                  annotation_text="High threshold",   annotation_position="bottom right",
                  annotation_font_color="#ef553b")

    fig.update_layout(
        title         = dict(text=f"{user_label}'s Burnout Trend", font=dict(color="#2d3561", family="Nunito", size=16)),
        height        = 400,
        hovermode     = "closest",
        paper_bgcolor = "white",
        plot_bgcolor  = "#f8f9ff",
        font          = dict(color="#2d3561", family="Nunito", size=12),
        xaxis         = dict(title="Date",      gridcolor="#e8ecf8", showgrid=True, color="#2d3561",tickfont=dict(size=11, color="#2d3561")),
        yaxis         = dict(title="CLI Score", gridcolor="#e8ecf8", showgrid=True, range=[0, 1.05], color="#2d3561",tickfont=dict(size=11, color="#2d3561")),
        legend        = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                             font=dict(color="#2d3561")),
        margin        = dict(l=20, r=20, t=60, b=20),
        hoverlabel    = dict(bgcolor="white", bordercolor="#a8a4ff",
                             font=dict(color="#2d3561", size=12)),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# Explainability Panel — accepts user_name for personalised heading
# ═══════════════════════════════════════════════════════════════════════════════

def render_explainability_panel(model, user_row, df_full, user_id, user_name=None):
    """
    Full explainability panel.

    Args:
        model     : loaded XGBClassifier
        user_row  : single-row DataFrame for selected user
        df_full   : full dataset for baseline computation
        user_id   : int
        user_name : str — display name (optional, falls back to "User {id}")
    """
    import streamlit as st
    from src.explainability.shap_explainer import (
        get_user_shap_values,
        get_user_baseline,
        build_natural_language_insights,
        build_baseline_table,
        FEATURE_COLUMNS,
    )

    display = user_name if user_name else f"User {user_id}"

    available = [c for c in FEATURE_COLUMNS if c in user_row.columns]
    X_user    = user_row[available].reset_index(drop=True)

    with st.spinner(f"Analysing {display}'s activity patterns..."):
        shap_vals, ev   = get_user_shap_values(model, X_user)
        user_bl, pop_bl = get_user_baseline(df_full, user_id)
        insights        = build_natural_language_insights(shap_vals, X_user, user_bl, pop_bl)
        comp_df         = build_baseline_table(X_user, user_bl, pop_bl)  # used for avg comparison cards

    st.markdown("---")
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            background:white;
            border:2.5px solid #a8a4ff;
            border-radius:16px;
            padding:10px 22px;
            box-shadow:4px 4px 0px #c8d0f0;
            font-family:'Nunito',sans-serif;
            font-weight:800;
            font-size:1.15rem;
            color:#2d3561;
            margin-bottom:16px;
        ">🔍 Why is <span style="color:#ff6b6b">{display}</span>'s burnout score this value?</div>
        """,
        unsafe_allow_html=True
    )

    # ── Section 1 : Insight Cards ─────────────────────────────────────────────
    st.markdown("#### 💡 Key Drivers")
    st.caption(f"Top 3 features pushing {display}'s burnout risk up or down right now.")

    for shap_val, text in insights:
        is_risk   = shap_val > 0
        bar_color = "#ff4b4b" if is_risk else "#00c48c"
        bg_color  = "rgba(255,75,75,0.09)" if is_risk else "rgba(0,196,140,0.09)"
        icon      = "🔴" if is_risk else "🟢"

        # Convert **text** → <strong>text</strong>
        parts    = text.split("**")
        rendered = "".join(
            f"<strong>{p}</strong>" if i % 2 == 1 else p
            for i, p in enumerate(parts)
        )

        st.markdown(
            f"""
            <div style="
                background:{bg_color};
                border-left:5px solid {bar_color};
                padding:13px 18px;
                border-radius:14px;
                margin-bottom:10px;
                color:#2d3561;
                font-size:0.92rem;
                font-family:'Nunito',sans-serif;
                font-weight:600;
                line-height:1.6;
                box-shadow:4px 4px 0px #c8d0f0;
                border-top:2px solid white;
                border-right:2px solid white;
            ">{icon}&nbsp; {rendered}</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 3 : Today vs Average — simple visual cards ───────────────────
    st.markdown(f"#### 📏 How {display} Compares to the Average Employee")
    st.caption("See at a glance where you stand on the key factors that affect burnout.")

    IMPORTANT = [
        ("task_switching",  "🔀 Task Switching",   "times switched between tasks", "switches"),
        ("work_duration",   "⏱️ Hours Worked",      "hours worked in the session",  "hrs"),
        ("typing_variance", "⌨️ Typing Steadiness", "how erratic your typing was",  "variance"),
        ("late_night",      "🌙 Late Night Work",   "worked after normal hours",    ""),
    ]

    cols = st.columns(len(IMPORTANT))

    for col, (feat, label, description, unit) in zip(cols, IMPORTANT):
        if feat not in X_user.columns:
            continue

        today = float(X_user[feat].values[0])
        avg   = float(pop_bl.get(feat, 0))

        if feat == "late_night":
            today_str = "Yes" if today == 1 else "No"
            avg_str   = f"{avg*100:.0f}% usually do"
            if today == 1 and avg < 0.5:
                status = "⚠️ You worked late"
                color  = "#ff4b4b"
                bg     = "rgba(255,75,75,0.09)"
            elif today == 0:
                status = "✅ Normal hours"
                color  = "#00c48c"
                bg     = "rgba(0,196,140,0.09)"
            else:
                status = "➡️ About average"
                color  = "#aaaaaa"
                bg     = "rgba(136,136,136,0.09)"
        else:
            today_str = f"{today:.0f} {unit}".strip()
            avg_str   = f"{avg:.0f} {unit}".strip()
            pct       = ((today - avg) / avg * 100) if avg != 0 else 0

            if pct > 15:
                status = f"⚠️ {abs(pct):.0f}% above average"
                color  = "#ff4b4b"
                bg     = "rgba(255,75,75,0.09)"
            elif pct < -15:
                status = f"✅ {abs(pct):.0f}% below average"
                color  = "#00c48c"
                bg     = "rgba(0,196,140,0.09)"
            else:
                status = "➡️ About average"
                color  = "#aaaaaa"
                bg     = "rgba(136,136,136,0.09)"

        col.markdown(
            f"""
            <div style="
                background:{bg};
                border:2.5px solid {color};
                border-radius:20px;
                padding:20px 16px;
                text-align:center;
                box-shadow:5px 5px 0px #c8d0f0;
                font-family:'Nunito',sans-serif;
            ">
                <div style="font-size:1.05rem;font-weight:800;color:#2d3561;margin-bottom:4px;">{label}</div>
                <div style="font-size:0.74rem;color:#8892b0;margin-bottom:12px;font-weight:600;">{description}</div>
                <div style="font-size:1.9rem;font-weight:900;color:{color};">{today_str}</div>
                <div style="font-size:0.74rem;color:#8892b0;margin-top:5px;font-weight:600;">avg employee: {avg_str}</div>
                <div style="margin-top:12px;font-size:0.82rem;font-weight:700;color:{color};
                    background:white;border-radius:20px;padding:4px 10px;display:inline-block;
                    box-shadow:2px 2px 0px #c8d0f0;">{status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )