"""Cryptographic service for AEGON.

Provides:
  - RSA-2048 key-pair generation / loading
  - SHA-256 file hashing
  - AES-256-GCM encrypt / decrypt
  - RSA-PSS digital signing & verification
"""
import hashlib
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


# ---------------------------------------------------------------------------
# RSA key management
# ---------------------------------------------------------------------------

def ensure_rsa_keys(keys_dir: str) -> None:
    """Generate RSA-2048 keypair if not already present."""
    priv_path = os.path.join(keys_dir, "private_key.pem")
    pub_path = os.path.join(keys_dir, "public_key.pem")

    if not os.path.exists(priv_path):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        os.makedirs(keys_dir, exist_ok=True)
        with open(priv_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
        with open(pub_path, "wb") as f:
            f.write(
                private_key.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )


def _load_private_key(keys_dir: str):
    priv_path = os.path.join(keys_dir, "private_key.pem")
    with open(priv_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


def _load_public_key(keys_dir: str):
    pub_path = os.path.join(keys_dir, "public_key.pem")
    with open(pub_path, "rb") as f:
        return serialization.load_pem_public_key(f.read(), backend=default_backend())


# ---------------------------------------------------------------------------
# SHA-256 hashing
# ---------------------------------------------------------------------------

def compute_sha256(data: bytes) -> str:
    """Return hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# RSA digital signature
# ---------------------------------------------------------------------------

def sign_hash(hash_hex: str, keys_dir: str) -> str:
    """Sign the SHA-256 hex string with the server RSA private key.

    Returns hex-encoded RSA-PSS signature.
    """
    private_key = _load_private_key(keys_dir)
    signature = private_key.sign(
        hash_hex.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature.hex()


def verify_signature(hash_hex: str, signature_hex: str, keys_dir: str) -> bool:
    """Verify RSA-PSS signature. Returns True if valid."""
    try:
        public_key = _load_public_key(keys_dir)
        public_key.verify(
            bytes.fromhex(signature_hex),
            hash_hex.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------

def aes_encrypt(plaintext: bytes) -> tuple[bytes, str, str]:
    """Encrypt plaintext with AES-256-GCM.

    Returns:
        (ciphertext_bytes, key_hex, nonce_hex)
    """
    key = os.urandom(32)   # 256-bit key
    nonce = os.urandom(12)  # 96-bit GCM nonce
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return ciphertext, key.hex(), nonce.hex()


def aes_decrypt(ciphertext: bytes, key_hex: str, nonce_hex: str) -> bytes:
    """Decrypt AES-256-GCM ciphertext.

    Raises:
        cryptography.exceptions.InvalidTag – if ciphertext or key is corrupt.
    """
    key = bytes.fromhex(key_hex)
    nonce = bytes.fromhex(nonce_hex)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
