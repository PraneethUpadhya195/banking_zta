import pandas as pd
from sklearn.linear_model import LogisticRegression
import os

def derive_ml_scores():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'processed_ieee_ml_ready.csv')
    
    print("Loading ML-ready dataset...")
    df = pd.read_csv(csv_path)
    
    # 1. Define Features (X) and Target (y)
    features = [
        'is_mobile_device', 
        'is_missing_device_signature', 
        'is_foreign_ip', 
        'is_distance_anomaly', 
        'is_high_risk_network'
    ]
    
    X = df[features]
    y = df['isFraud']
    
    print("Training Logistic Regression Model...")
    # class_weight='balanced' is crucial for highly imbalanced fraud data
    model = LogisticRegression(class_weight='balanced', random_state=42)
    model.fit(X, y)
    
    # 2. Extract the Beta Coefficients
    coefficients = model.coef_[0]
    
    # 3. Scale to OPA Points
    # A standard beta coefficient is usually between 0.1 and 3.0. 
    # We multiply by 15 so the highest risk signals hit around 30-45 OPA points.
    scaling_factor = 15  
    
    print("\n" + "="*50)
    print("ML-DERIVED OPA ZERO TRUST SCORES")
    print("="*50)
    print("Feature                     | Beta Coef | OPA Score")
    print("-" * 50)
    
    opa_scores = {}
    for feature, coef in zip(features, coefficients):
        # We only care about positive correlation to fraud (ignore negatives)
        if coef > 0:
            opa_score = int(round(coef * scaling_factor))
            opa_scores[feature] = opa_score
            print(f"{feature:<27} | {coef:>9.4f} | {opa_score:>9} pts")
        else:
            print(f"{feature:<27} | {coef:>9.4f} | Ignored (Negative)")
            
    print("="*50)
    print("\nUpdate your OPA data.json with these exact values!")

if __name__ == "__main__":
    derive_ml_scores()