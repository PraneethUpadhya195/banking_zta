import pandas as pd
import matplotlib.pyplot as plt

# Load + merge
df_trans = pd.read_csv("train_transaction.csv")
df_id = pd.read_csv("train_identity.csv")

df = df_trans.merge(df_id, on="TransactionID", how="left")

# Clean
df["DeviceType"] = df["DeviceType"].fillna("unknown")

# Fraud rate
dev = df.groupby("DeviceType")["isFraud"].mean().reset_index()

# Plot
colors = ["#4CAF50", "#FF9800", "#F44336"]

plt.figure(figsize=(7,5))
plt.bar(dev["DeviceType"], dev["isFraud"], color=colors)

plt.title("Fraud Rate by Device Type")
plt.xlabel("Device Type")
plt.ylabel("Fraud Probability")

for i, v in enumerate(dev["isFraud"]):
    plt.text(i, v + 0.001, f"{v:.4f}", ha='center')

plt.tight_layout()
plt.show()