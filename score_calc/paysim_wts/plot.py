import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# TEMPORAL PREP
# =========================
df = pd.read_csv("paysim.csv")
# Create hour + bucket
df["hour"] = df["step"] % 24

def get_bucket(h):
    if h < 6: return "late_night"
    elif h < 12: return "morning"
    elif h < 18: return "afternoon"
    else: return "evening"

df["hour_bucket"] = df["hour"].apply(get_bucket)

# Order buckets properly
order = ["morning", "afternoon", "evening", "late_night"]

temp = df.groupby("hour_bucket")["isFraud"].mean().reindex(order).reset_index()

# =========================
# PLOT 1: TEMPORAL
# =========================

colors_temp = ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]

plt.figure(figsize=(8,5))
plt.bar(temp["hour_bucket"], temp["isFraud"], color=colors_temp)

plt.title("Fraud Rate by Time of Day")
plt.xlabel("Time Bucket")
plt.ylabel("Fraud Probability")

# Value labels
for i, v in enumerate(temp["isFraud"]):
    plt.text(i, v + 0.0002, f"{v:.4f}", ha='center')

plt.tight_layout()
plt.show()


# =========================
# VELOCITY PREP
# =========================

# Ensure sorted
df = df.sort_values(by=["nameOrig", "step"])

# Compute step_diff if not already present
df["step_diff"] = df.groupby("nameOrig")["step"].diff()

# Bucket it
df["step_diff_bucket"] = pd.cut(
    df["step_diff"],
    bins=[-1, 5, 10, 20, 50, 1000]
)

vel = df.groupby("step_diff_bucket")["isFraud"].mean().reset_index()

# Convert to string for plotting
vel["step_diff_bucket"] = vel["step_diff_bucket"].astype(str)

# =========================
# PLOT 2: VELOCITY
# =========================

colors_vel = ["#9C27B0", "#03A9F4", "#8BC34A", "#FF5722", "#FFC107"]

plt.figure(figsize=(8,5))
plt.bar(vel["step_diff_bucket"], vel["isFraud"], color=colors_vel)

plt.title("Fraud Rate vs Transaction Gap")
plt.xlabel("Transaction Gap (step_diff)")
plt.ylabel("Fraud Probability")

plt.xticks(rotation=45)

# Value labels
for i, v in enumerate(vel["isFraud"]):
    plt.text(i, v + 0.0001, f"{v:.4f}", ha='center')

plt.tight_layout()
plt.show()