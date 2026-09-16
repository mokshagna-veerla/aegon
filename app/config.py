"""Configuration classes for AEGON.
Prototype uses SQLite. Switch DATABASE_URL env var for MySQL.
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "aegon-dev-secret-changeme-in-production")

    # SQLite for prototype; swap to MySQL in production:
    # mysql+pymysql://user:pass@host/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'aegon.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Vault & key storage paths
    VAULT_DIR = os.path.join(BASE_DIR, "vault", "encrypted")
    KEYS_DIR = os.path.join(BASE_DIR, "keys")
    BLOCKCHAIN_LEDGER = os.path.join(BASE_DIR, "blockchain_ledger.json")

    # Upload limits
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

    # Allowed file types
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "doc", "docx"}

    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
