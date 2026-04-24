import pandas as pd
import os

def step_one_baseline():
    print("Loading PaySim dataset... (This might take a few seconds)")
    
    # 1. Get the directory where this python script lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Join it with the CSV filename
    # MAKE SURE THIS MATCHES YOUR DOWNLOADED FILE NAME EXACTLY
    csv_path = os.path.join(script_dir, './PaySim/PS_20174392719_1491204439457_log.csv')
    
    # 3. Load using the absolute path
    df = pd.read_csv(csv_path) 
    
    print(f"Total rows loaded: {len(df):,}")

    # We only care about user-to-user transfers for your architecture.
    df_transfers = df[df['type'] == 'TRANSFER'].copy()
    
    total_transfers = len(df_transfers)
    fraudulent_transfers = len(df_transfers[df_transfers['isFraud'] == 1])
    legitimate_transfers = total_transfers - fraudulent_transfers
    
    # Calculate P(Fraud)
    p_fraud = fraudulent_transfers / total_transfers
    
    print("\n--- BASELINE METRICS ---")
    print(f"Total Transfers Analyzed: {total_transfers:,}")
    print(f"Legitimate Transfers: {legitimate_transfers:,}")
    print(f"Fraudulent Transfers: {fraudulent_transfers:,}")
    print(f"Baseline P(Fraud): {p_fraud:.6f} ({p_fraud * 100:.2f}%)")
    print("\n--- DATASET FEATURES ---")
    print("Columns:", df_transfers.columns.tolist())
    print("\nSample Row:")
    print(df_transfers.head(1).to_dict('records')[0])
    
if __name__ == "__main__":
    step_one_baseline()