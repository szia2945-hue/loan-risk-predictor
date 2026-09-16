"""
app.py
Flask web application serving the credit-risk model, with user accounts
and per-user prediction history.
"""
import csv
import io
import os
import socket
import webbrowser
from threading import Timer

from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_login import login_required, current_user
from dotenv import load_dotenv
import joblib
import numpy as np

from extensions import db, login_manager, limiter
from models import User, Prediction
from auth import auth_bp

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")

FEATURES = [
    "age", "income", "loan_amount", "credit_score",
    "employment_years", "existing_loans", "debt_to_income",
]

# Model artifacts load karo
model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)


def risk_level(prob):
    if prob < 0.3:
        return "Low"
    elif prob < 0.6:
        return "Medium"
    return "High"


def create_app():
    app = Flask(__name__)

    # --- Secret key ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")

    # --- Database URL: Render par Postgres, local par SQLite ---
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ledger.db')}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Free Postgres idle connections kaat deta hai ---
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # --- Extensions init ---
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    # --- Blueprint ---
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/")
    def root():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("index.html")

    @app.route("/history")
    @login_required
    def history():
        predictions = (
            Prediction.query.filter_by(user_id=current_user.id)
            .order_by(Prediction.created_at.desc())
            .all()
        )

        total = len(predictions)
        avg_prob = round(sum(p.default_probability for p in predictions) / total * 100, 1) if total else 0
        counts = {"Low": 0, "Medium": 0, "High": 0}
        for p in predictions:
            counts[p.risk_level] = counts.get(p.risk_level, 0) + 1

        stats = {
            "total": total,
            "avg_prob": avg_prob,
            "low": counts.get("Low", 0),
            "medium": counts.get("Medium", 0),
            "high": counts.get("High", 0),
        }

        return render_template("history.html", predictions=predictions, stats=stats)

    @app.route("/history/export")
    @login_required
    def export_history():
        predictions = (
            Prediction.query.filter_by(user_id=current_user.id)
            .order_by(Prediction.created_at.desc())
            .all()
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["created_at", *FEATURES, "default_probability", "default_prediction", "risk_level"]
        )
        for p in predictions:
            writer.writerow([
                p.created_at.strftime("%Y-%m-%d %H:%M"),
                p.age, p.income, p.loan_amount, p.credit_score,
                p.employment_years, p.existing_loans, p.debt_to_income,
                p.default_probability, p.default_prediction, p.risk_level,
            ])

        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=ledger_history.csv"},
        )

    @app.route("/history/<int:prediction_id>/delete", methods=["POST"])
    @login_required
    def delete_history_item(prediction_id):
        record = Prediction.query.filter_by(
            id=prediction_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(record)
        db.session.commit()
        return redirect(url_for("history"))

    @app.route("/favicon.ico")
    def favicon():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" fill="#0A1930"/>'
            '<text x="32" y="45" font-family="Georgia,serif" font-size="38" '
            'font-weight="700" fill="#C9A15A" text-anchor="middle">&#167;</text>'
            "</svg>"
        )
        return Response(svg, mimetype="image/svg+xml")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/predict", methods=["POST"])
    @limiter.limit("30 per minute")
    def predict():
        try:
            data = request.get_json(force=True) if request.is_json else request.form

            values = []
            for f in FEATURES:
                if f not in data or data[f] in (None, ""):
                    return jsonify({"error": f"Missing field: {f}"}), 400
                values.append(float(data[f]))

            X = np.array(values).reshape(1, -1)
            X_scaled = scaler.transform(X)

            proba = float(model.predict_proba(X_scaled)[0][1])
            prediction = int(model.predict(X_scaled)[0])
            level = risk_level(proba)

            if current_user.is_authenticated:
                record = Prediction(
                    user_id=current_user.id,
                    age=values[0], income=values[1], loan_amount=values[2],
                    credit_score=values[3], employment_years=values[4],
                    existing_loans=values[5], debt_to_income=values[6],
                    default_probability=round(proba, 4),
                    default_prediction=prediction,
                    risk_level=level,
                )
                db.session.add(record)
                db.session.commit()

            result = {
                "default_prediction": prediction,
                "default_probability": round(proba, 4),
                "risk_level": level,
            }
            return jsonify(result)

        except ValueError:
            return jsonify({"error": "All fields must be numeric"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- Tables create karo (Postgres ke liye zaroori) ---
    with app.app_context():
        db.create_all()

    return app


app = create_app()


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def open_browser(port):
    ip = get_local_ip()
    webbrowser.open_new(f"http://{ip}:{port}/")


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", 5000))

    if not debug_mode or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser, args=[port]).start()

    app.run(debug=debug_mode, host="0.0.0.0", port=port)