"""
train.py
Trains a RandomForestClassifier on the loan dataset, evaluates it,
and saves the trained model + scaler to disk using joblib.
"""

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

FEATURES = [
    "age", "income", "loan_amount", "credit_score",
    "employment_years", "existing_loans", "debt_to_income",
]

def main():
    df = pd.read_csv("loan_data.csv")

    X = df[FEATURES]
    y = df["default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    print("Model Evaluation on Test Set")
    print("-" * 40)
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.3f}")
    print(f"Precision: {precision_score(y_test, y_pred):.3f}")
    print(f"Recall   : {recall_score(y_test, y_pred):.3f}")
    print(f"F1 Score : {f1_score(y_test, y_pred):.3f}")
    print(f"ROC AUC  : {roc_auc_score(y_test, y_proba):.3f}")

    importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\nFeature Importances")
    print("-" * 40)
    print(importances)

    joblib.dump(model, "model.pkl")
    joblib.dump(scaler, "scaler.pkl")
    print("\nSaved model.pkl and scaler.pkl")

if __name__ == "__main__":
    main()
