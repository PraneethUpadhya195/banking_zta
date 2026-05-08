import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# --- Load datasets ---
df_trans = pd.read_csv("train_transaction.csv")
df_id = pd.read_csv("train_identity.csv")

# --- Merge ---
df = df_trans.merge(df_id, on="TransactionID", how="left")

# --- Select only needed columns ---
cols = ["addr1", "addr2", "dist1", "dist2", "isFraud"]
df = df[cols]

# --- Handle missing values ---
df["addr1"] = df["addr1"].fillna(-1)
df["addr2"] = df["addr2"].fillna(-1)
df["dist1"] = df["dist1"].fillna(df["dist1"].median())
df["dist2"] = df["dist2"].fillna(df["dist2"].median())

# --- Features / target ---
X = df[["addr1", "addr2", "dist1", "dist2"]]
y = df["isFraud"]

# --- Scale ---
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# --- Train Logistic Regression ---
model = LogisticRegression(max_iter=1000)
model.fit(X_scaled, y)

# --- Extract coefficients ---
features = ["addr1", "addr2", "dist1", "dist2"]
coeffs = model.coef_[0]

print("\n=== Raw Coefficients ===")
for f, c in zip(features, coeffs):
    print(f"{f}: {round(c, 4)}")

# --- Convert to penalties ---
k = 10
penalties = k * coeffs

print("\n=== Location Penalties (ZTA style) ===")
for f, p in zip(features, penalties):
    # ZTA rule: ignore negative (no reward)
    p = max(0, p)
    print(f"{f}: {round(p, 2)}")