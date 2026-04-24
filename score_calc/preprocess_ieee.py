import pandas as pd
import os

def preprocess_ieee():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    trans_path = os.path.join(script_dir, './ieee-fraud-detection/train_transaction.csv')
    id_path = os.path.join(script_dir, './ieee-fraud-detection/train_identity.csv')

    print("Loading datasets... (This will consume ~2GB of RAM and take a moment)")
    df_trans = pd.read_csv(trans_path)
    df_id = pd.read_csv(id_path)

    print("Merging Transaction and Identity data...")
    # Left merge: We keep all transactions, and attach device info if the hacker left any
    df = df_trans.merge(df_id, on='TransactionID', how='left')

    print("Engineering Zero Trust Features...")
    y = df['isFraud']

    # 1. Device Risk (Proxy for unregistered_device)
    df['is_mobile_device'] = (df['DeviceType'] == 'mobile').astype(int)
    df['is_missing_device_signature'] = df['DeviceType'].isnull().astype(int)

    # 2. IP Anomaly (Proxy for untrusted_ip)
    # addr2 == 87.0 is the domestic country. Anything else is suspicious.
    df['is_foreign_ip'] = ((df['addr2'].notnull()) & (df['addr2'] != 87.0)).astype(int)

    # 3. Impossible Travel (IP distance > 100 miles)
    df['is_distance_anomaly'] = (df['dist1'] > 100).astype(int)

    # 4. Network Risk (Anonymous / Burner domains)
    high_risk_emails = ['mail.com', 'protonmail.com', 'yopmail.com', 'anonymous.com']
    df['is_high_risk_network'] = df['P_emaildomain'].isin(high_risk_emails).astype(int)

    # Create the final, lightweight ML dataframe
    features = [
        'is_mobile_device', 
        'is_missing_device_signature', 
        'is_foreign_ip', 
        'is_distance_anomaly', 
        'is_high_risk_network'
    ]
    
    df_clean = df[features].copy()
    df_clean['isFraud'] = y

    # Save it so we don't have to do this heavy lifting again
    output_path = os.path.join(script_dir, 'processed_ieee_ml_ready.csv')
    df_clean.to_csv(output_path, index=False)

    print("\n" + "="*40)
    print("PREPROCESSING COMPLETE")
    print("="*40)
    print(f"Total Rows Processed: {len(df_clean):,}")
    print(f"Saved lightweight dataset to: {output_path}")
    print("Ready for Logistic Regression!")

if __name__ == "__main__":
    preprocess_ieee()