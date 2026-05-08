import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv("paysim.csv")

# --- Sort by user and time ---
df = df.sort_values(by=["nameOrig", "step"])

# --- Compute time gap between consecutive transactions (per user) ---
df["step_diff"] = df.groupby("nameOrig")["step"].diff()

# --- Define burst condition (tune threshold if needed) ---
# Here: another txn within 2 steps (~2 hours) = high velocity
df["high_velocity"] = (df["step_diff"] <= 10).astype(int)

# First transaction per user has NaN diff → not high velocity
df["high_velocity"] = df["high_velocity"].fillna(0)

# --- Baseline probability ---
P_F = df["isFraud"].mean()

# --- Group ---
grouped = df.groupby("high_velocity")["isFraud"].agg(["count", "sum"]).reset_index()
grouped.columns = ["condition", "total", "fraud"]

# --- Laplace smoothing ---
grouped["P_F_given_C"] = (grouped["fraud"] + 1) / (grouped["total"] + 2)

# --- Compute weights ---
grouped["W_C"] = grouped["P_F_given_C"] / P_F

# --- Convert to penalty ---
k = 15
grouped["penalty"] = k * np.log(grouped["W_C"])

# --- ZTA rule: no negative reward ---
grouped["penalty"] = grouped["penalty"].clip(lower=0, upper=15)

# --- Extract high velocity penalty ---
velocity_penalty = grouped.loc[grouped["condition"] == 1, "penalty"].values[0]

# --- Output ---
print("\n=== Velocity Penalty ===")
print(f"High Velocity (step_diff <= 10): {round(velocity_penalty, 2)}")

print("\n=== Debug Table ===")
print(grouped)