"""
generate_data.py
Generates a realistic synthetic loan/credit-risk dataset and saves it as CSV.
In a real-world version, you'd replace this with a public dataset
(e.g. Kaggle 'Loan Prediction' or 'German Credit Data').
"""

import numpy as np
import pandas as pd

np.random.seed(42)

N = 2000

age = np.random.randint(21, 65, N)
income = np.random.normal(55000, 20000, N).clip(15000, 200000)
loan_amount = np.random.normal(15000, 8000, N).clip(1000, 50000)
credit_score = np.random.normal(650, 90, N).clip(300, 850)
employment_years = np.random.randint(0, 30, N)
existing_loans = np.random.randint(0, 5, N)
debt_to_income = (loan_amount / income) + np.random.normal(0, 0.05, N)
debt_to_income = debt_to_income.clip(0, 2)

# Create a "risk score" using a weighted formula + noise, then threshold it
risk_score = (
    -0.004 * credit_score
    + 3.0 * debt_to_income
    - 0.00002 * income
    + 0.05 * existing_loans
    - 0.02 * employment_years
    + np.random.normal(0, 0.5, N)
)

# Convert risk score into binary default label (1 = default, 0 = repaid)
threshold = np.percentile(risk_score, 75)  # top 25% riskiest -> default
default = (risk_score > threshold).astype(int)

df = pd.DataFrame({
    "age": age,
    "income": income.round(2),
    "loan_amount": loan_amount.round(2),
    "credit_score": credit_score.round(0).astype(int),
    "employment_years": employment_years,
    "existing_loans": existing_loans,
    "debt_to_income": debt_to_income.round(3),
    "default": default,
})

df.to_csv("loan_data.csv", index=False)
print(f"Generated {len(df)} rows. Default rate: {df['default'].mean():.2%}")
print(df.head())
