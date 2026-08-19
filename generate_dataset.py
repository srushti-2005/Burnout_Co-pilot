import pandas as pd
import numpy as np

np.random.seed(42)

users = 20
sessions_per_user = 30
total_rows = users * sessions_per_user

# Generate base dates
dates = pd.date_range(start="2025-01-01", periods=sessions_per_user)

data_rows = []

for user in range(1, users + 1):

    for i in range(sessions_per_user):

        base_date = dates[i]

        # random hour/minute for realistic sessions
        hour = np.random.randint(8, 23)
        minute = np.random.randint(0, 60)

        timestamp = base_date + pd.Timedelta(hours=hour, minutes=minute)

        typing_mean = np.random.randint(40, 81)
        typing_variance = np.random.randint(5, 26)
        task_switching = np.random.randint(10, 61)
        work_duration = np.random.randint(4, 13)
        late_night = np.random.randint(0, 2)

        score = 0

        if typing_variance > 18:
            score += 1
        if task_switching > 40:
            score += 1
        if work_duration > 9:
            score += 1
        if late_night == 1:
            score += 1

        burnout_label = 1 if score >= 2 else 0

        data_rows.append([
            user,
            timestamp,
            typing_mean,
            typing_variance,
            task_switching,
            work_duration,
            late_night,
            burnout_label
        ])

df = pd.DataFrame(data_rows, columns=[
    "user_id",
    "timestamp",
    "typing_mean",
    "typing_variance",
    "task_switching",
    "work_duration",
    "late_night",
    "burnout_label"
])

df = df.sort_values(["user_id", "timestamp"])

df.to_csv("data/burnout_dataset.csv", index=False)

print("Dataset generated successfully.")
print("Total rows:", len(df))
print(df.head())