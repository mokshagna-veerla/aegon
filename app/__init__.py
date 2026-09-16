"""AEGON Flask Application Factory."""
import os
from flask import Flask
from app.config import config
from app.extensions import db, login_manager


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config[config_name])

    # Ensure directories exist
    os.makedirs(app.config["VAULT_DIR"], exist_ok=True)
    os.makedirs(app.config["KEYS_DIR"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.cases import cases_bp
    from app.blueprints.documents import documents_bp
    from app.blueprints.verify import verify_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cases_bp, url_prefix="/cases")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(verify_bp, url_prefix="/verify")

    # Root redirect
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("cases.list_cases"))
        return redirect(url_for("auth.login"))

    # Create all tables
    with app.app_context():
        db.create_all()
        # Ensure RSA keys exist
        from app.services.crypto_service import ensure_rsa_keys
        ensure_rsa_keys(app.config["KEYS_DIR"])

    return app
