# src/suggestions/suggestion_engine.py
"""
Generates real-time warnings and personalised suggestions
based on the user's latest session data and CLI score.
"""

from dataclasses import dataclass


@dataclass
class Suggestion:
    level:   str    # "danger" | "warning" | "success"
    icon:    str
    title:   str
    message: str


def get_suggestions(
    cli: float,
    typing_mean:     float = 0,
    typing_variance: float = 0,
    task_switching:  int   = 0,
    work_duration:   float = 0,
    late_night:      int   = 0,
    user_name:       str   = "there",
) -> list[Suggestion]:
    """
    Returns a list of Suggestion objects based on current metrics.
    Priority: danger → warning → success
    """
    suggestions = []

    # ── HIGH BURNOUT RISK ─────────────────────────────────────────────────────
    if cli >= 0.75:
        suggestions.append(Suggestion(
            level="danger", icon="🚨",
            title="High Burnout Risk Detected",
            message=f"Hi {user_name}, your burnout score is critically high at {cli*100:.0f}%. "
                    "Please stop working and take a proper break of at least 30 minutes."
        ))

    elif cli >= 0.5:
        suggestions.append(Suggestion(
            level="warning", icon="⚠️",
            title="Moderate Burnout Risk",
            message=f"Your burnout score is {cli*100:.0f}%. Consider taking a short break "
                    "and reviewing your workload for the rest of the day."
        ))

    else:
        suggestions.append(Suggestion(
            level="success", icon="✅",
            title="You're Doing Well",
            message=f"Your burnout risk is low ({cli*100:.0f}%). Keep maintaining your "
                    "current work-rest balance."
        ))

    # ── LATE NIGHT WORK ───────────────────────────────────────────────────────
    if late_night == 1:
        suggestions.append(Suggestion(
            level="danger", icon="🌙",
            title="Late Night Work Detected",
            message="Working late at night significantly increases burnout risk and "
                    "disrupts your sleep cycle. Try to wrap up within the next 30 minutes."
        ))

    # ── LONG WORK HOURS ───────────────────────────────────────────────────────
    if work_duration >= 10:
        suggestions.append(Suggestion(
            level="danger", icon="⏰",
            title="Extremely Long Work Session",
            message=f"You've been working for {work_duration:.1f} hours. This is "
                    "well beyond healthy limits. Stop and rest — productivity drops "
                    "sharply after 8 hours."
        ))
    elif work_duration >= 8:
        suggestions.append(Suggestion(
            level="warning", icon="⏱️",
            title="Long Work Session",
            message=f"You've worked {work_duration:.1f} hours today. Take a proper "
                    "break — a 20-minute walk can significantly restore focus."
        ))
    elif work_duration >= 6:
        suggestions.append(Suggestion(
            level="warning", icon="☕",
            title="Consider a Break",
            message=f"{work_duration:.1f} hours of work — time for a short 5-minute "
                    "break. Stand up, stretch, and hydrate."
        ))

    # ── HIGH TASK SWITCHING ───────────────────────────────────────────────────
    if task_switching >= 50:
        suggestions.append(Suggestion(
            level="danger", icon="🔀",
            title="Extreme Task Switching",
            message=f"You've switched tasks {task_switching} times this session. "
                    "Constant context switching drains mental energy. Try the Pomodoro "
                    "technique — 25 min focused work, then 5 min break."
        ))
    elif task_switching >= 30:
        suggestions.append(Suggestion(
            level="warning", icon="🔄",
            title="High Task Switching",
            message=f"{task_switching} task switches detected. Try to batch similar "
                    "tasks together and reduce interruptions for the next hour."
        ))

    # ── ERRATIC TYPING (high variance) ────────────────────────────────────────
    if typing_variance >= 20:
        suggestions.append(Suggestion(
            level="warning", icon="⌨️",
            title="Irregular Typing Pattern",
            message="Your typing is very inconsistent — this often indicates fatigue "
                    "or distraction. Take 5 minutes away from the screen."
        ))

    # ── VERY LOW TYPING (possible idle / unfocused) ───────────────────────────
    if 0 < typing_mean < 10 and work_duration > 1:
        suggestions.append(Suggestion(
            level="warning", icon="💤",
            title="Low Activity Detected",
            message="Very little typing detected this session. If you're feeling "
                    "unmotivated, try a brief physical activity to reset focus."
        ))

    return suggestions


def get_suggestion_cards_html(suggestions: list[Suggestion]) -> str:
    """
    Renders suggestion list as styled HTML cards for st.markdown().
    Returns HTML string.
    """
    color_map = {
        "danger":  ("#ff4b4b", "rgba(255,75,75,0.10)"),
        "warning": ("#ffa15a", "rgba(255,161,90,0.10)"),
        "success": ("#00c48c", "rgba(0,196,140,0.10)"),
    }

    html = ""
    for s in suggestions:
        stroke, bg = color_map.get(s.level, ("#888", "rgba(136,136,136,0.1)"))
        html += f"""
        <div style="
            background:{bg};
            border-left:5px solid {stroke};
            padding:14px 18px;
            border-radius:14px;
            margin-bottom:12px;
            font-family:'Nunito',sans-serif;
            box-shadow:4px 4px 0px #c8d0f0;
        ">
            <div style="font-size:1rem;font-weight:800;color:#2d3561;margin-bottom:4px;">
                {s.icon} &nbsp; {s.title}
            </div>
            <div style="font-size:0.88rem;color:#444;line-height:1.6;">
                {s.message}
            </div>
        </div>
        """
    return html