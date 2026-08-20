def get_risk_label(score):
    """
    Convert CLI score into a human-readable burnout risk label.

    Parameters
    ----------
    score : float
        Cognitive Load Index (CLI) score between 0 and 1.

    Returns
    -------
    tuple
        (risk_label, message)
    """

    score = float(score)

    if score < 0.4:
        label = "🟢 Low Risk"
        message = "Everything looks normal. Stay focused!"

    elif score < 0.75:
        label = "🟡 Moderate Risk"
        message = "Take a short 5-minute break soon."

    else:
        label = "🔴 High Risk"
        message = "Immediate rest recommended. Digital burnout likely."

    return label, message