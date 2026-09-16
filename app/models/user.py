"""User model with role-based access control."""
from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Role:
    POLICE_IO = "police_io"
    FORENSIC = "forensic"
    LEGAL = "legal"
    ADMIN = "admin"

    ALL = [POLICE_IO, FORENSIC, LEGAL, ADMIN]

    LABELS = {
        POLICE_IO: "Police / IO",
        FORENSIC: "Forensic Expert",
        LEGAL: "Legal / Judge",
        ADMIN: "Administrator",
    }

    # Roles that can upload documents
    UPLOADERS = {POLICE_IO, FORENSIC, ADMIN}
    # Roles that can simulate tampering
    TAMPERERS = {ADMIN}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, default="")
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.POLICE_IO)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    audit_trails = db.relationship("AuditTrail", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self) -> str:
        return Role.LABELS.get(self.role, self.role)

    @property
    def can_upload(self) -> bool:
        return self.role in Role.UPLOADERS

    @property
    def can_tamper(self) -> bool:
        return self.role in Role.TAMPERERS

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def __repr__(self) -> str:
        return f"<User {self.username} [{self.role}]>"


@login_manager.user_loader
def load_user(user_id: int):
    return db.session.get(User, int(user_id))
