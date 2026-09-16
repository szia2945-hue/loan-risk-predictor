"""
tests/test_app.py
Test suite covering health check, auth (signup/login/logout), the
login-gated dashboard/history, and the public /predict API.
Run with:  pytest -v
"""

import os
import tempfile

import pytest


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret"

    from app import create_app

    flask_app = create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


VALID_PAYLOAD = {
    "age": 35,
    "income": 55000,
    "loan_amount": 15000,
    "credit_score": 650,
    "employment_years": 5,
    "existing_loans": 1,
    "debt_to_income": 0.30,
}


def signup(client, username="jane", email="jane@example.com", password="secret123"):
    return client.post(
        "/auth/signup",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_signup_then_dashboard_accessible(client):
    resp = signup(client)
    assert resp.status_code == 200
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"LEDGER" in resp.data


def test_signup_duplicate_username_rejected(client):
    signup(client)
    client.get("/auth/logout")
    resp = signup(client, email="other@example.com")
    assert b"already taken" in resp.data


def test_login_logout(client):
    signup(client)
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"identifier": "jane", "password": "secret123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_login_wrong_password(client):
    signup(client)
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"identifier": "jane", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_predict_valid_payload_public(client):
    # /predict works without login (used by the curl example in the README)
    resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "default_probability" in body
    assert body["risk_level"] in ("Low", "Medium", "High")
    assert 0.0 <= body["default_probability"] <= 1.0


def test_predict_missing_field(client):
    payload = VALID_PAYLOAD.copy()
    del payload["credit_score"]
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_predict_non_numeric_field(client):
    payload = VALID_PAYLOAD.copy()
    payload["age"] = "not-a-number"
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_logged_in_predict_saved_to_history(client):
    signup(client)
    client.post("/predict", json=VALID_PAYLOAD)
    resp = client.get("/history")
    assert resp.status_code == 200
    assert b"55,000" in resp.data or b"55000" in resp.data or b"$55,000" in resp.data


def test_history_requires_login(client):
    resp = client.get("/history", follow_redirects=False)
    assert resp.status_code == 302
