import pandas as pd
import numpy as np


def get_7_day_forecast(current_cli):
    """
    Generate a simple 7-day burnout risk forecast.

    Parameters
    ----------
    current_cli : float
        Latest CLI score from the dataset.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns:
        Date | CLI
    """

    # Safety check
    try:
        current_cli = float(current_cli)
    except (ValueError, TypeError):
        current_cli = 0.5

    # Generate next 7 dates (starting tomorrow)
    dates = pd.date_range(
        start=pd.Timestamp.now().normalize() + pd.Timedelta(days=1),
        periods=7
    )

    # Simulated burnout trend
    trend = []

    for i in range(7):

        # small upward trend with noise
        value = current_cli + (i * 0.015) + np.random.uniform(-0.01, 0.01)

        # keep score within valid bounds
        value = np.clip(value, 0, 1)

        trend.append(value)

    forecast_df = pd.DataFrame({
        "Date": dates,
        "CLI": trend
    })

    return forecast_df