import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv("paysim.csv")

# --- Extract hour ---
df["hour"] = df["step"] % 24

# --- Bucket hours ---
def get_hour_bucket(hour):
    if 0 <= hour < 6:
        return "late_night"
    elif 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"

df["hour_bucket"] = df["hour"].apply(get_hour_bucket)

# --- Baseline probability ---
P_F = df["isFraud"].mean()

# --- Group ---
grouped = df.groupby("hour_bucket")["isFraud"].agg(["count", "sum"]).reset_index()
grouped.columns = ["bucket", "total", "fraud"]

# --- Laplace smoothing ---
grouped["P_F_given_C"] = (grouped["fraud"] + 1) / (grouped["total"] + 2)

# --- Compute weights ---
grouped["W_C"] = grouped["P_F_given_C"] / P_F

# --- Convert to penalty ---
k = 15
grouped["penalty"] = k * np.log(grouped["W_C"])

# --- ZTA rule: no negative reward ---
grouped["penalty"] = grouped["penalty"].clip(lower=0, upper=15)

# --- Output ---
print("\n=== Temporal Weights ===")
for _, row in grouped.iterrows():
    print(f"{row['bucket']}: {round(row['penalty'], 2)}")

print("\n=== Debug Table ===")
print(grouped)