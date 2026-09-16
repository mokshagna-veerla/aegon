"""AuditTrail model – immutable log of every action on documents."""
from app.extensions import db
from datetime import datetime


class AuditTrail(db.Model):
    __tablename__ = "audit_trails"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True, index=True)
    case_id = db.Column(db.Integer, nullable=True)

    action = db.Column(db.String(50), nullable=False)   # upload / view / verify / tamper / login / logout
    status = db.Column(db.String(20), nullable=False, default="success")  # success / failure / warning
    detail = db.Column(db.Text, nullable=True)           # Free text detail
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_trails")
    document = db.relationship("Document", back_populates="audit_trails")

    # Action constants
    ACTION_UPLOAD = "upload"
    ACTION_VIEW = "view"
    ACTION_VERIFY = "verify"
    ACTION_TAMPER = "tamper_simulate"
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_CREATE_CASE = "create_case"

    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    STATUS_MISMATCH = "mismatch"
    STATUS_WARNING = "warning"

    @property
    def action_label(self) -> str:
        labels = {
            "upload": "Document Uploaded",
            "view": "Document Viewed",
            "verify": "Integrity Verified",
            "tamper_simulate": "⚠ Tamper Simulated",
            "login": "Login",
            "logout": "Logout",
            "create_case": "Case Created",
        }
        return labels.get(self.action, self.action.title())

    @property
    def status_class(self) -> str:
        classes = {
            "success": "text-emerald-400",
            "failure": "text-rose-400",
            "mismatch": "text-rose-400",
            "warning": "text-yellow-400",
        }
        return classes.get(self.status, "text-slate-400")

    def __repr__(self) -> str:
        return f"<AuditTrail {self.action} by user {self.user_id} at {self.timestamp}>"
