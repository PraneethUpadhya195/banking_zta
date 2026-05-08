import pandas as pd
import numpy as np

# --- Load datasets ---
df_trans = pd.read_csv("train_transaction.csv")
df_id = pd.read_csv("train_identity.csv")

# --- Merge ---
df = df_trans.merge(df_id, on="TransactionID", how="left")

# --- Keep relevant columns ---
df = df[["isFraud", "DeviceType", "DeviceInfo"]]

# --- Fill missing ---
df["DeviceType"] = df["DeviceType"].fillna("unknown")
df["DeviceInfo"] = df["DeviceInfo"].fillna("unknown")

# --- Baseline probability ---
P_F = df["isFraud"].mean()

# ================================
# 🔹 DeviceType (Clean signal)
# ================================

grouped_type = df.groupby("DeviceType")["isFraud"].agg(["count", "sum"]).reset_index()
grouped_type.columns = ["DeviceType", "total", "fraud"]

# Laplace smoothing
grouped_type["P_F_given_C"] = (grouped_type["fraud"] + 1) / (grouped_type["total"] + 2)

# Weight
grouped_type["W_C"] = grouped_type["P_F_given_C"] / P_F

# Penalty
k = 15
grouped_type["penalty"] = k * np.log(grouped_type["W_C"])
grouped_type["penalty"] = grouped_type["penalty"].clip(lower=0, upper=15)

print("\n=== DeviceType Penalties ===")
print(grouped_type)

# ================================
# 🔹 DeviceInfo (Reduce categories)
# ================================

# Keep top 20 most frequent devices
top_devices = df["DeviceInfo"].value_counts().head(20).index

df["DeviceInfo_reduced"] = df["DeviceInfo"].apply(
    lambda x: x if x in top_devices else "other"
)

grouped_info = df.groupby("DeviceInfo_reduced")["isFraud"].agg(["count", "sum"]).reset_index()
grouped_info.columns = ["DeviceInfo", "total", "fraud"]

# Laplace smoothing
grouped_info["P_F_given_C"] = (grouped_info["fraud"] + 1) / (grouped_info["total"] + 2)

# Weight
grouped_info["W_C"] = grouped_info["P_F_given_C"] / P_F

# Penalty
grouped_info["penalty"] = k * np.log(grouped_info["W_C"])
grouped_info["penalty"] = grouped_info["penalty"].clip(lower=0, upper=15)

print("\n=== DeviceInfo Penalties ===")
print(grouped_info)