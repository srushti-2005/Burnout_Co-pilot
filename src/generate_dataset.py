import pandas as pd
import numpy as np

np.random.seed(42)

days = 110  # You can choose between 90–120

dates = pd.date_range(end=pd.Timestamp.today(), periods=days)

data = {
    "date": dates,
    "typing_mean": np.random.randint(40, 81, days),
    "typing_variance": np.random.randint(5, 26, days),
    "task_switching": np.random.randint(10, 61, days),
    "work_duration": np.random.randint(4, 13, days),
    "late_night": np.random.randint(0, 2, days)
}

df = pd.DataFrame(data)
def assign_burnout(row):
    score = 0
    
    if row["typing_variance"] > 18:
        score += 1
    if row["task_switching"] > 40:
        score += 1
    if row["work_duration"] > 9:
        score += 1
    if row["late_night"] == 1:
        score += 1
        
    return 1 if score >= 2 else 0

df["burnout_label"] = df.apply(assign_burnout, axis=1)
print(df["burnout_label"].value_counts())
print(df.head())
df.to_csv("data/burnout_dataset.csv", index=False)
print("Dataset saved successfully.")