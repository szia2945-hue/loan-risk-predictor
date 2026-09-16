"""
models.py
SQLAlchemy models: User (auth) and Prediction (per-user assessment history).
"""

from datetime import datetime

from flask_login import UserMixin

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predictions = db.relationship(
        "Prediction",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Prediction.created_at.desc()",
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    age = db.Column(db.Float, nullable=False)
    income = db.Column(db.Float, nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    credit_score = db.Column(db.Float, nullable=False)
    employment_years = db.Column(db.Float, nullable=False)
    existing_loans = db.Column(db.Float, nullable=False)
    debt_to_income = db.Column(db.Float, nullable=False)

    default_probability = db.Column(db.Float, nullable=False)
    default_prediction = db.Column(db.Integer, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "age": self.age,
            "income": self.income,
            "loan_amount": self.loan_amount,
            "credit_score": self.credit_score,
            "employment_years": self.employment_years,
            "existing_loans": self.existing_loans,
            "debt_to_income": self.debt_to_income,
            "default_probability": self.default_probability,
            "default_prediction": self.default_prediction,
            "risk_level": self.risk_level,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }
