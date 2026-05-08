import pandas as pd
import numpy as np

df = pd.read_csv("paysim.csv")

# Compute weights
temporal_weights, temporal_debug = compute_temporal_weights(df)
velocity_penalty, velocity_debug = compute_velocity_weight(df)

# Recompute velocity column for scoring
df = df.sort_values(by="step")
df["txn_count_5"] = (
    df.groupby("nameOrig")["step"]
    .transform(lambda x: x.rolling(window=5, min_periods=1).count())
)

# Apply scoring
df["zta_score"] = df.apply(lambda row: compute_zta_score(row, temporal_weights, velocity_penalty), axis=1)