"""Documents routes: upload, view (watermarked), stream."""
import os
import uuid
from datetime import datetime

from flask import (
    render_template, redirect, url_for, flash, request,
    current_app, send_file, abort, jsonify, Response
)
from flask_login import login_required, current_user

from app.blueprints.documents import documents_bp
from app.extensions import db
from app.models.document import Document
from app.models.case import Case
from app.models.audit import AuditTrail
from app.models.user import Role


def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _get_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    return mime_map.get(ext, "application/octet-stream")


@documents_bp.route("/cases/<int:case_id>/upload", methods=["GET", "POST"])
@login_required
def upload(case_id: int):
    if not current_user.can_upload:
        flash("Access denied: Only Police/IO, Forensic Expert, or Admin can upload documents.", "error")
        return redirect(url_for("cases.case_detail", case_id=case_id))

    case = Case.query.get_or_404(case_id)

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part in the request.", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(request.url)

        if not _allowed_file(file.filename):
            flash("File type not allowed. Supported: PDF, PNG, JPG, JPEG, TIFF.", "error")
            return redirect(request.url)

        raw_bytes = file.read()
        if not raw_bytes:
            flash("Uploaded file is empty.", "error")
            return redirect(request.url)

        original_filename = file.filename
        mime_type = _get_mime(original_filename)

        # ── Phase 2: Cryptographic pipeline ──────────────────────────────
        from app.services.crypto_service import compute_sha256, sign_hash, aes_encrypt
        from app.services.blockchain_service import record_document as bc_record

        sha256_hash = compute_sha256(raw_bytes)
        keys_dir = current_app.config["KEYS_DIR"]
        digital_signature = sign_hash(sha256_hash, keys_dir)

        ciphertext, aes_key_hex, aes_nonce_hex = aes_encrypt(raw_bytes)

        # Store encrypted blob
        vault_dir = current_app.config["VAULT_DIR"]
        stored_filename = f"{uuid.uuid4().hex}.enc"
        storage_path = os.path.join(vault_dir, stored_filename)
        with open(storage_path, "wb") as f:
            f.write(ciphertext)

        # ── Persist to DB ─────────────────────────────────────────────────
        doc = Document(
            case_id=case_id,
            filename=stored_filename,
            original_filename=original_filename,
            storage_path=storage_path,
            file_size=len(raw_bytes),
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            digital_signature=digital_signature,
            aes_key=aes_key_hex,
            aes_nonce=aes_nonce_hex,
            uploaded_by=current_user.id,
            timestamp=datetime.utcnow(),
        )
        db.session.add(doc)
        db.session.flush()  # get doc.id

        # ── Blockchain anchoring ──────────────────────────────────────────
        ledger_path = current_app.config["BLOCKCHAIN_LEDGER"]
        tx_hash = bc_record(
            ledger_path=ledger_path,
            doc_id=doc.id,
            case_id=case_id,
            sha256_hash=sha256_hash,
            digital_signature=digital_signature,
            uploader_username=current_user.username,
            filename=original_filename,
        )
        doc.blockchain_tx = tx_hash

        # ── OCR (async-like, best effort) ─────────────────────────────────
        from app.services.ocr_service import extract_text_from_bytes
        extracted = extract_text_from_bytes(raw_bytes, mime_type)
        if extracted:
            doc.extracted_text = extracted[:10000]  # cap at 10k chars

        # ── Audit trail ───────────────────────────────────────────────────
        trail = AuditTrail(
            user_id=current_user.id,
            document_id=doc.id,
            case_id=case_id,
            action=AuditTrail.ACTION_UPLOAD,
            status=AuditTrail.STATUS_SUCCESS,
            detail=f"Uploaded '{original_filename}' | SHA-256: {sha256_hash[:16]}... | TX: {tx_hash[:16]}...",
            ip_address=request.remote_addr,
        )
        db.session.add(trail)
        db.session.commit()

        flash(f"Document '{original_filename}' uploaded and anchored to blockchain successfully.", "success")
        return redirect(url_for("cases.case_detail", case_id=case_id))

    return render_template("documents/upload.html", case=case)


@documents_bp.route("/<int:doc_id>/view")
@login_required
def view_document(doc_id: int):
    """Render the secure view-only document viewer page."""
    doc = Document.query.get_or_404(doc_id)

    trail = AuditTrail(
        user_id=current_user.id,
        document_id=doc_id,
        case_id=doc.case_id,
        action=AuditTrail.ACTION_VIEW,
        status=AuditTrail.STATUS_SUCCESS,
        detail=f"Viewed '{doc.original_filename}'",
        ip_address=request.remote_addr,
    )
    db.session.add(trail)
    db.session.commit()

    return render_template("documents/viewer.html", doc=doc)


@documents_bp.route("/<int:doc_id>/stream")
@login_required
def stream_document(doc_id: int):
    """Decrypt document, apply watermark, and stream as PDF (in memory only)."""
    doc = Document.query.get_or_404(doc_id)

    if not os.path.exists(doc.storage_path):
        abort(404)

    # Read encrypted blob
    with open(doc.storage_path, "rb") as f:
        ciphertext = f.read()

    # Decrypt
    from app.services.crypto_service import aes_decrypt
    try:
        plaintext = aes_decrypt(ciphertext, doc.aes_key, doc.aes_nonce)
    except Exception:
        abort(500)

    # Apply watermark
    from app.services.watermark_service import apply_watermark
    watermarked = apply_watermark(
        file_bytes=plaintext,
        mime_type=doc.mime_type or "application/pdf",
        viewer_username=current_user.username,
        viewer_role=current_user.role_label,
        timestamp=datetime.utcnow(),
    )

    import io
    return Response(
        watermarked,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )
