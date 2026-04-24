import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, roc_curve, auc
import os

def generate_graphs():
    # 1. Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'processed_ieee_ml_ready.csv')
    
    print("Loading data...")
    df = pd.read_csv(csv_path)
    
    features = ['is_mobile_device', 'is_missing_device_signature', 
                'is_foreign_ip', 'is_distance_anomaly', 'is_high_risk_network']
    X = df[features]
    y = df['isFraud']

    # Split data to evaluate on unseen data (Good academic practice!)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    print("Training Model...")
    model = LogisticRegression(class_weight='balanced', random_state=42)
    model.fit(X_train, y_train)

    # ==========================================
    # GRAPH 1: Feature Importance (OPA Scores)
    # ==========================================
    print("Generating Figure 1: Feature Importance...")
    plt.figure(figsize=(10, 6))
    
    # Get coefficients
    coefs = pd.DataFrame({
        'Feature': ['Mobile Device', 'Missing Signature', 'Foreign IP', 'Distance Anomaly', 'High-Risk Email'],
        'Coefficient': model.coef_[0]
    })
    coefs = coefs.sort_values(by='Coefficient', ascending=False)
    
    # Plot
    sns.barplot(x='Coefficient', y='Feature', data=coefs, palette='coolwarm')
    #plt.title('Figure 1: Logistic Regression Coefficients for ZTA Telemetry', fontsize=14)
    plt.xlabel('Log-Odds Coefficient (Used for OPA Score)', fontsize=12)
    plt.axvline(x=0, color='black', linestyle='--')
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'fig1_feature_importance.png'), dpi=300)
    plt.close()

    # ==========================================
    # GRAPH 2: The Confusion Matrix
    # ==========================================
    print("Generating Figure 2: Confusion Matrix...")
    # Get predictions
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Allowed (Negative)', 'Blocked/MFA (Positive)'],
                yticklabels=['Legit Tx (Negative)', 'Fraud Tx (Positive)'])
    #plt.title('Figure 2: Zero Trust Engine Confusion Matrix', fontsize=14)
    plt.ylabel('Actual Truth', fontsize=12)
    plt.xlabel('ZTA Engine Decision', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'fig2_confusion_matrix.png'), dpi=300)
    plt.close()

    # ==========================================
    # GRAPH 3: The ROC Curve (Threshold Tradeoff)
    # ==========================================
    print("Generating Figure 3: ROC Curve...")
    y_prob = model.predict_proba(X_test)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate (Friction for Normal Users)', fontsize=12)
    plt.ylabel('True Positive Rate (Hackers Caught)', fontsize=12)
    #plt.title('Figure 3: Receiver Operating Characteristic (ROC)', fontsize=14)
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, 'fig3_roc_curve.png'), dpi=300)
    plt.close()

    print("\nSUCCESS! Three high-resolution images saved to your score_calc folder.")

if __name__ == "__main__":
    generate_graphs()