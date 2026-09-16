"""Auth routes: login, logout, register (admin only)."""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth_bp
from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditTrail


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("cases.list_cases"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username, is_active=True).first()

        if user and user.check_password(password):
            login_user(user, remember=False)

            # Audit log
            trail = AuditTrail(
                user_id=user.id,
                action=AuditTrail.ACTION_LOGIN,
                status=AuditTrail.STATUS_SUCCESS,
                detail=f"Successful login from {request.remote_addr}",
                ip_address=request.remote_addr,
            )
            db.session.add(trail)
            db.session.commit()

            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("cases.list_cases"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    trail = AuditTrail(
        user_id=current_user.id,
        action=AuditTrail.ACTION_LOGOUT,
        status=AuditTrail.STATUS_SUCCESS,
        ip_address=request.remote_addr,
    )
    db.session.add(trail)
    db.session.commit()

    logout_user()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if not current_user.is_admin:
        flash("Access denied: Admin only.", "error")
        return redirect(url_for("cases.list_cases"))

    roles = [(r, Role.LABELS[r]) for r in Role.ALL]

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")
        role = request.form.get("role", Role.POLICE_IO)

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
        elif role not in Role.ALL:
            flash("Invalid role selected.", "error")
        else:
            user = User(username=username, full_name=full_name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"User '{username}' created successfully with role '{Role.LABELS[role]}'.", "success")
            return redirect(url_for("auth.register"))

    return render_template("auth/register.html", roles=roles)
