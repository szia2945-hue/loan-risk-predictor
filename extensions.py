"""
extensions.py
Central place for Flask extension instances so app.py, auth.py, and
models.py can all import them without circular-import problems.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access your dashboard."
login_manager.login_message_category = "info"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
)