"""Document model – stores encrypted evidence with cryptographic metadata."""
from app.extensions import db
from datetime import datetime


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)   # Path to AES-encrypted blob
    file_size = db.Column(db.Integer, nullable=False, default=0)
    mime_type = db.Column(db.String(100), nullable=True)

    # Cryptographic fields
    sha256_hash = db.Column(db.String(64), nullable=False)          # Hash of ORIGINAL plaintext
    digital_signature = db.Column(db.Text, nullable=False)          # RSA signature (hex) of hash
    aes_key = db.Column(db.String(64), nullable=False)             # AES-256 key (hex) – prototype only
    aes_nonce = db.Column(db.String(24), nullable=False)           # GCM nonce (hex)

    # Blockchain anchor
    blockchain_tx = db.Column(db.String(64), nullable=True)        # Ledger tx_hash reference

    # Upload metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Tamper flag (set by admin simulation)
    tampered = db.Column(db.Boolean, default=False, nullable=False)

    # OCR extracted text for search
    extracted_text = db.Column(db.Text, nullable=True)

    # Relationships
    case = db.relationship("Case", back_populates="documents")
    uploader = db.relationship("User", foreign_keys=[uploaded_by])
    audit_trails = db.relationship("AuditTrail", back_populates="document", lazy="dynamic")

    @property
    def short_hash(self) -> str:
        return self.sha256_hash[:16] + "..." if self.sha256_hash else "N/A"

    @property
    def extension(self) -> str:
        return self.original_filename.rsplit(".", 1)[-1].lower() if "." in self.original_filename else ""

    @property
    def is_pdf(self) -> bool:
        return self.extension == "pdf"

    @property
    def is_image(self) -> bool:
        return self.extension in {"png", "jpg", "jpeg", "tiff", "bmp", "gif"}

    def __repr__(self) -> str:
        return f"<Document {self.id}: {self.original_filename}>"
