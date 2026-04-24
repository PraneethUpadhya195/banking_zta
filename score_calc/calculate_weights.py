import pandas as pd
import os

def derive_signal_weights():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, './PaySim/PS_20174392719_1491204439457_log.csv')
    
    print("Loading dataset...")
    df = pd.read_csv(csv_path)
    df = df[df['type'] == 'TRANSFER'].copy()
    
    # --- 1. FEATURE ENGINEERING ---
    # Convert 'step' to a 24-hour clock (0-23)
    df['hour_of_day'] = df['step'] % 24
    
    # Define Off-Hours (e.g., 1 AM to 5 AM)
    df['is_off_hours'] = df['hour_of_day'].isin([1, 2, 3, 4, 5])
    
    # Define High Amount (Using your previous ZTA threshold of 50,000)
    df['is_high_amount'] = df['amount'] > 50000
    
    # --- 2. BASELINE PROBABILITY ---
    p_fraud_baseline = df['isFraud'].mean()
    
    # --- 3. CONDITIONAL PROBABILITIES ---
    # P(Fraud | Off-Hours)
    off_hours_df = df[df['is_off_hours'] == True]
    p_fraud_given_off_hours = off_hours_df['isFraud'].mean() if len(off_hours_df) > 0 else 0
    
    # P(Fraud | High Amount)
    high_amount_df = df[df['is_high_amount'] == True]
    p_fraud_given_high_amount = high_amount_df['isFraud'].mean() if len(high_amount_df) > 0 else 0
    
    # --- 4. CALCULATING THE RISK MULTIPLIER (WEIGHT) ---
    weight_off_hours = p_fraud_given_off_hours / p_fraud_baseline if p_fraud_baseline > 0 else 0
    weight_high_amount = p_fraud_given_high_amount / p_fraud_baseline if p_fraud_baseline > 0 else 0
    
    # --- OUTPUT RESULTS ---
    print("\n" + "="*40)
    print("STATISTICAL RISK WEIGHT DERIVATION")
    print("="*40)
    print(f"Baseline P(Fraud): {p_fraud_baseline*100:.4f}%")
    
    print("\n--- OFF-HOURS SIGNAL ---")
    print(f"Transactions during Off-Hours: {len(off_hours_df):,}")
    print(f"P(Fraud | Off-Hours): {p_fraud_given_off_hours*100:.4f}%")
    print(f"Risk Multiplier: {weight_off_hours:.2f}x")
    
    print("\n--- HIGH AMOUNT SIGNAL (>50k) ---")
    print(f"Transactions > 50k: {len(high_amount_df):,}")
    print(f"P(Fraud | High Amount): {p_fraud_given_high_amount*100:.4f}%")
    print(f"Risk Multiplier: {weight_high_amount:.2f}x")
    print("="*40)

if __name__ == "__main__":
    derive_signal_weights()