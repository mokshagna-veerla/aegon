"""Verify blueprint."""
from flask import Blueprint

verify_bp = Blueprint("verify", __name__, template_folder="templates")

from app.blueprints.verify import routes  # noqa: F401, E402
