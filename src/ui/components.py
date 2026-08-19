# src/ui/components.py

import plotly.graph_objects as go
import pandas as pd


def create_burnout_gauge(score, title="Real-time Burnout Risk"):
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0

    score = max(0, min(score, 1))
    percentage = score * 100

    risk_label = "LOW RISK" if percentage < 40 else ("MODERATE RISK" if percentage < 75 else "HIGH RISK")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        number={'suffix': "%", 'font': {'size': 44, 'color': '#1e1b4b', 'family': 'Plus Jakarta Sans'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 0, 'showticklabels': False},
            'bar': {'color': "rgba(139, 92, 246, 0.8)", 'thickness': 0.28},
            'steps': [
                {'range': [0, 40], 'color': "rgba(16, 185, 129, 0.18)"},
                {'range': [40, 75], 'color': "rgba(245, 158, 11, 0.18)"},
                {'range': [75, 100], 'color': "rgba(239, 68, 68, 0.18)"},
            ],
            'threshold': {
                'line': {'color': "#ec4899", 'width': 4},
                'thickness': 0.85,
                'value': percentage,
            }
        }
    ))

    fig.add_annotation(
        text=f"<b>{risk_label}</b>",
        x=0.5, y=0.18, showarrow=False,
        font=dict(size=12, color="#8b5cf6", family="Plus Jakarta Sans")
    )

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1b4b", family="Plus Jakarta Sans"),
    )
    return fig


def create_burnout_trend_chart(user_df: pd.DataFrame, user_label):
    df = user_df.copy().reset_index(drop=True)

    def risk_label(cli):
        if cli < 0.4: return "Low Risk"
        elif cli < 0.7: return "Moderate Risk"
        else: return "High Risk"

    df["risk_label"] = df["CLI"].apply(risk_label)
    color_map = {"Low Risk": "#10b981", "Moderate Risk": "#f59e0b", "High Risk": "#ef4444"}
    df["pt_color"] = df["risk_label"].map(color_map)

    fig = go.Figure()

    # Soft gradient background fill under trend line
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["CLI"],
        mode="lines+markers",
        line=dict(color="#8b5cf6", width=3.5, shape='spline'),
        marker=dict(color=df["pt_color"], size=9, line=dict(color="white", width=2)),
        fill='tozeroy',
        fillcolor='rgba(236, 72, 153, 0.06)',
        hovertemplate="<b>%{x|%b %d, %H:%M}</b><br>CLI: <b>%{y:.3f}</b><extra></extra>",
        showlegend=False
    ))

    fig.add_hline(y=0.4, line_dash="dash", line_color="rgba(16, 185, 129, 0.4)",
                  annotation_text="Low/Medium", annotation_position="bottom right",
                  annotation_font=dict(color="#10b981", size=10, family="Plus Jakarta Sans"))
    fig.add_hline(y=0.7, line_dash="dash", line_color="rgba(239, 68, 68, 0.4)",
                  annotation_text="High Risk", annotation_position="bottom right",
                  annotation_font=dict(color="#ef4444", size=10, family="Plus Jakarta Sans"))

    fig.update_layout(
        height=340,
        margin=dict(l=10, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1b4b", family="Plus Jakarta Sans"),
        xaxis=dict(gridcolor="#f1f5f9", showgrid=True, color="#64748b"),
        yaxis=dict(gridcolor="#f1f5f9", showgrid=True, range=[0, 1.05], color="#64748b"),
        hoverlabel=dict(bgcolor="white", bordercolor="#8b5cf6", font=dict(color="#1e1b4b", size=12)),
    )
    return fig


def render_explainability_panel(model, user_row, df_full, user_id, user_name=None):
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
    X_user = user_row[available].reset_index(drop=True)

    with st.spinner(f"Analysing activity patterns..."):
        shap_vals, ev = get_user_shap_values(model, X_user)
        user_bl, pop_bl = get_user_baseline(df_full, user_id)
        insights = build_natural_language_insights(shap_vals, X_user, user_bl, pop_bl)

    st.markdown(f"""
    <div style="margin-top: 28px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
        <div>
            <h3 style="margin: 0; font-size: 1.25rem;">✨ AI Insights for {display}</h3>
            <p style="color: #828ba0; font-size: 0.84rem; margin: 0;">Personalised insights based on your recent activity</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for shap_val, text in insights:
        is_risk = shap_val > 0
        icon = "🔴" if is_risk else "🟢"
        badge_bg = "rgba(239, 68, 68, 0.08)" if is_risk else "rgba(16, 185, 129, 0.08)"
        border_col = "rgba(239, 68, 68, 0.2)" if is_risk else "rgba(16, 185, 129, 0.2)"
        
        parts = text.split("**")
        rendered = "".join(f"<strong>{p}</strong>" if i % 2 == 1 else p for i, p in enumerate(parts))

        st.markdown(f"""
        <div style="
            background: {badge_bg};
            border: 1.5px solid {border_col};
            border-radius: 16px;
            padding: 14px 18px;
            margin-bottom: 10px;
            font-size: 0.88rem;
            color: #1e1b4b;
            line-height: 1.6;
        ">{icon}&nbsp; {rendered}</div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### ✦ How {display} Compares")
    st.caption("See where you stand relative to typical workload parameters.")

    IMPORTANT = [
        ("task_switching", "⚡ Task Switching", "switches"),
        ("work_duration", "⏱️ Hours Worked", "hrs"),
        ("typing_variance", "⌨️ Typing Steadiness", "variance"),
        ("late_night", "🌙 Late Night Work", ""),
    ]

    cols = st.columns(len(IMPORTANT))
    for col, (feat, label, unit) in zip(cols, IMPORTANT):
        if feat not in X_user.columns:
            continue

        today = float(X_user[feat].values[0])
        avg = float(pop_bl.get(feat, 0))

        if feat == "late_night":
            today_str = "Yes" if today == 1 else "No"
            status = "⚠️ Worked Late" if today == 1 else "✅ Normal Hours"
            color = "#ef4444" if today == 1 else "#10b981"
        else:
            today_str = f"{today:.0f} {unit}".strip()
            pct = ((today - avg) / avg * 100) if avg != 0 else 0
            if pct > 15:
                status = f"↑ {abs(pct):.0f}% above average"
                color = "#ef4444"
            elif pct < -15:
                status = f"↓ {abs(pct):.0f}% below average"
                color = "#10b981"
            else:
                status = "= About average"
                color = "#8b5cf6"

        col.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.9);
            border: 1.5px solid #eef2f6;
            border-radius: 20px;
            padding: 18px 14px;
            text-align: center;
            box-shadow: 0 8px 24px -4px rgba(130, 140, 200, 0.1);
        ">
            <div style="font-size: 0.85rem; font-weight: 700; color: #64748b; margin-bottom: 8px;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #1e1b4b;">{today_str}</div>
            <div style="margin-top: 10px; font-size: 0.76rem; font-weight: 700; color: {color};
                background: rgba(255,255,255,0.9); border: 1px solid {color}; border-radius: 20px; padding: 4px 8px; display: inline-block;">
                {status}
            </div>
        </div>
        """, unsafe_allow_html=True)