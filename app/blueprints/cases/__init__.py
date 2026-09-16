"""Cases blueprint."""
from flask import Blueprint

cases_bp = Blueprint("cases", __name__, template_folder="templates")

from app.blueprints.cases import routes  # noqa: F401, E402
