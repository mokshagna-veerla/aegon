"""Case model – the top-level container for evidence documents."""
from app.extensions import db
from datetime import datetime


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open")  # open / closed / archived
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = db.relationship("Document", back_populates="case", lazy="dynamic", cascade="all, delete-orphan")
    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def document_count(self) -> int:
        return self.documents.count()

    @property
    def status_badge(self) -> str:
        badges = {
            "open": "badge-green",
            "closed": "badge-gray",
            "archived": "badge-yellow",
        }
        return badges.get(self.status, "badge-gray")

    def __repr__(self) -> str:
        return f"<Case {self.case_number}: {self.title}>"
