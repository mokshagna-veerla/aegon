"""Verify blueprint routes: integrity check and tamper simulation."""
import os

from flask import jsonify, request, current_app, render_template, abort
from flask_login import login_required, current_user

from app.blueprints.verify import verify_bp
from app.extensions import db
from app.models.document import Document
from app.models.audit import AuditTrail


@verify_bp.route("/<int:doc_id>", methods=["GET"])
@login_required
def verify_document(doc_id: int):
    """Chain-of-custody integrity verification engine.

    Workflow:
    1. Retrieve anchored SHA-256 hash from blockchain_ledger.json
    2. Read encrypted ciphertext from vault
    3. Decrypt with stored AES key/nonce
    4. Re-hash decrypted bytes with SHA-256
    5. Compare hashes → MATCH or MISMATCH
    """
    doc = Document.query.get_or_404(doc_id)

    ledger_path = current_app.config["BLOCKCHAIN_LEDGER"]
    from app.services.blockchain_service import get_document_record
    record = get_document_record(ledger_path, doc_id)

    if not record:
        return jsonify({
            "status": "ERROR",
            "message": "Document not found in blockchain ledger. Cannot verify.",
            "doc_id": doc_id,
        }), 404

    anchored_hash = record.get("sha256_hash", "")

    # Read ciphertext from vault
    if not os.path.exists(doc.storage_path):
        return jsonify({
            "status": "ERROR",
            "message": "Encrypted vault file not found.",
            "doc_id": doc_id,
        }), 404

    with open(doc.storage_path, "rb") as f:
        ciphertext = f.read()

    # Decrypt
    from app.services.crypto_service import aes_decrypt, compute_sha256
    try:
        plaintext = aes_decrypt(ciphertext, doc.aes_key, doc.aes_nonce)
    except Exception as e:
        # AES-GCM authentication tag mismatch — ciphertext has been tampered
        _record_audit(doc, "MISMATCH", f"AES-GCM decryption failed (tag mismatch): {e}")
        return jsonify({
            "status": "MISMATCH",
            "verdict": "TAMPER ALERT",
            "message": "AES-GCM authentication tag failed. Ciphertext has been modified in the vault.",
            "anchored_hash": anchored_hash,
            "computed_hash": "DECRYPTION_FAILED",
            "blockchain_tx": record.get("tx_hash", ""),
            "anchored_at": record.get("anchored_at", ""),
            "doc_id": doc_id,
            "filename": doc.original_filename,
        })

    # Re-hash
    computed_hash = compute_sha256(plaintext)
    match = computed_hash == anchored_hash

    # Also verify RSA signature
    from app.services.crypto_service import verify_signature
    sig_valid = verify_signature(anchored_hash, doc.digital_signature, current_app.config["KEYS_DIR"])

    status = "MATCH" if match else "MISMATCH"
    verdict = "AUTHENTIC – Integrity Verified ✓" if match else "TAMPER ALERT – Hash Mismatch ✗"

    _record_audit(
        doc,
        status,
        f"Anchored: {anchored_hash[:16]}... | Computed: {computed_hash[:16]}... | Sig: {'✓' if sig_valid else '✗'}"
    )

    return jsonify({
        "status": status,
        "verdict": verdict,
        "anchored_hash": anchored_hash,
        "computed_hash": computed_hash,
        "hashes_match": match,
        "signature_valid": sig_valid,
        "blockchain_tx": record.get("tx_hash", ""),
        "anchored_at": record.get("anchored_at", ""),
        "doc_id": doc_id,
        "filename": doc.original_filename,
        "uploader": record.get("uploader", ""),
        "tampered_flag": doc.tampered,
    })


@verify_bp.route("/<int:doc_id>/tamper", methods=["POST"])
@login_required
def simulate_tamper(doc_id: int):
    """Admin-only: Flip a byte in the encrypted vault file to simulate tampering.

    This corrupts the AES-GCM authentication tag, causing both decryption
    failure AND hash mismatch on next verification — demonstrating tamper detection.
    """
    if not current_user.can_tamper:
        return jsonify({"error": "Access denied. Admin role required."}), 403

    doc = Document.query.get_or_404(doc_id)

    if not os.path.exists(doc.storage_path):
        return jsonify({"error": "Vault file not found."}), 404

    with open(doc.storage_path, "r+b") as f:
        content = bytearray(f.read())
        if len(content) < 10:
            return jsonify({"error": "File too small to tamper."}), 400
        # Flip byte at position 5 (within the ciphertext body)
        content[5] ^= 0xFF
        f.seek(0)
        f.write(content)

    doc.tampered = True
    trail = AuditTrail(
        user_id=current_user.id,
        document_id=doc_id,
        case_id=doc.case_id,
        action=AuditTrail.ACTION_TAMPER,
        status=AuditTrail.STATUS_WARNING,
        detail=f"DEMO TAMPER: Byte-flip at offset 5 in vault/{doc.filename}",
        ip_address=request.remote_addr,
    )
    db.session.add(trail)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Tamper simulation applied to document #{doc_id}. Run verification to see MISMATCH alert.",
        "doc_id": doc_id,
        "filename": doc.original_filename,
    })


@verify_bp.route("/<int:doc_id>/restore", methods=["POST"])
@login_required
def restore_document(doc_id: int):
    """Admin-only: Restore document by re-flipping the tampered byte."""
    if not current_user.can_tamper:
        return jsonify({"error": "Access denied. Admin role required."}), 403

    doc = Document.query.get_or_404(doc_id)

    if not os.path.exists(doc.storage_path):
        return jsonify({"error": "Vault file not found."}), 404

    with open(doc.storage_path, "r+b") as f:
        content = bytearray(f.read())
        content[5] ^= 0xFF  # XOR again restores original byte
        f.seek(0)
        f.write(content)

    doc.tampered = False
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Document #{doc_id} restored. Integrity verification should now pass.",
    })


def _record_audit(doc: Document, status: str, detail: str) -> None:
    from flask_login import current_user
    trail = AuditTrail(
        user_id=current_user.id,
        document_id=doc.id,
        case_id=doc.case_id,
        action=AuditTrail.ACTION_VERIFY,
        status=AuditTrail.STATUS_SUCCESS if status == "MATCH" else AuditTrail.STATUS_MISMATCH,
        detail=detail,
        ip_address=request.remote_addr,
    )
    db.session.add(trail)
    db.session.commit()


@verify_bp.route("/audit-ss", methods=["POST"])
@login_required
def audit_screenshot():
    """Record a screenshot attempt in the audit trail.

    Called by the client-side screenshot prevention system whenever a
    suspicious action is detected (PrtScn, window blur, getDisplayMedia, etc.)
    """
    data = request.get_json(silent=True) or {}
    doc_id = data.get("doc_id")
    method = data.get("method", "unknown")[:80]  # cap length

    trail = AuditTrail(
        user_id=current_user.id,
        document_id=doc_id if isinstance(doc_id, int) else None,
        action="screenshot_attempt",
        status=AuditTrail.STATUS_WARNING,
        detail=f"Screenshot prevention triggered | method={method} | user={current_user.username} | ip={request.remote_addr}",
        ip_address=request.remote_addr,
    )
    db.session.add(trail)
    db.session.commit()

    return jsonify({"logged": True, "method": method})
