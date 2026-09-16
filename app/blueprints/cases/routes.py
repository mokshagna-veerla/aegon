"""Cases routes: list, create, detail."""
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text as sa_text

from app.blueprints.cases import cases_bp
from app.extensions import db
from app.models.case import Case
from app.models.audit import AuditTrail
from app.models.user import User


@cases_bp.route("/", methods=["GET"])
@login_required
def list_cases():
    search = request.args.get("q", "").strip()
    query = Case.query.order_by(Case.created_at.desc())

    if search:
        query = query.filter(
            Case.title.ilike(f"%{search}%") |
            Case.case_number.ilike(f"%{search}%") |
            Case.description.ilike(f"%{search}%")
        )

    cases = query.all()

    # Dashboard stats
    from app.models.document import Document
    total_cases = Case.query.count()
    total_docs = Document.query.count()
    recent_audits = AuditTrail.query.order_by(AuditTrail.timestamp.desc()).limit(8).all()

    return render_template(
        "cases/list.html",
        cases=cases,
        search=search,
        total_cases=total_cases,
        total_docs=total_docs,
        recent_audits=recent_audits,
    )


@cases_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_case():
    if request.method == "POST":
        case_number = request.form.get("case_number", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not case_number or not title:
            flash("Case number and title are required.", "error")
            return render_template("cases/create.html")

        if Case.query.filter_by(case_number=case_number).first():
            flash(f"Case number '{case_number}' already exists.", "error")
            return render_template("cases/create.html")

        case = Case(
            case_number=case_number,
            title=title,
            description=description,
            created_by=current_user.id,
            status="open",
        )
        db.session.add(case)
        db.session.flush()  # get ID before commit

        trail = AuditTrail(
            user_id=current_user.id,
            case_id=case.id,
            action=AuditTrail.ACTION_CREATE_CASE,
            status=AuditTrail.STATUS_SUCCESS,
            detail=f"Case '{case_number}' created: {title}",
            ip_address=request.remote_addr,
        )
        db.session.add(trail)
        db.session.commit()

        flash(f"Case {case_number} created successfully.", "success")
        return redirect(url_for("cases.case_detail", case_id=case.id))

    return render_template("cases/create.html")


@cases_bp.route("/<int:case_id>", methods=["GET"])
@login_required
def case_detail(case_id: int):
    case = Case.query.get_or_404(case_id)
    documents = case.documents.order_by(sa_text("timestamp DESC")).all()
    search = request.args.get("q", "").strip()

    if search:
        from app.models.document import Document
        documents = case.documents.filter(
            Document.original_filename.ilike(f"%{search}%") |
            Document.extracted_text.ilike(f"%{search}%")
        ).all()

    return render_template(
        "cases/detail.html",
        case=case,
        documents=documents,
        search=search,
    )


@cases_bp.route("/<int:case_id>/update-status", methods=["POST"])
@login_required
def update_status(case_id: int):
    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403
    case = Case.query.get_or_404(case_id)
    new_status = request.json.get("status")
    if new_status in ("open", "closed", "archived"):
        case.status = new_status
        db.session.commit()
        return jsonify({"status": new_status})
    return jsonify({"error": "Invalid status"}), 400
