"""Seed script – creates all DB tables and populates demo users + a sample case.

Run once after first setup:
    python seed_db.py

Safe to re-run (idempotent – skips existing users).
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.case import Case


DEMO_USERS = [
    {
        "username": "officer_raj",
        "full_name": "Inspector Rajesh Kumar",
        "email": "raj.kumar@police.gov.in",
        "password": "Pass@1234",
        "role": Role.POLICE_IO,
    },
    {
        "username": "dr_forensics",
        "full_name": "Dr. Priya Sharma",
        "email": "priya.sharma@forensics.gov.in",
        "password": "Pass@1234",
        "role": Role.FORENSIC,
    },
    {
        "username": "judge_sharma",
        "full_name": "Hon. Justice A.K. Sharma",
        "email": "ak.sharma@judiciary.gov.in",
        "password": "Pass@1234",
        "role": Role.LEGAL,
    },
    {
        "username": "admin",
        "full_name": "AEGON System Administrator",
        "email": "admin@ncrb.gov.in",
        "password": "Admin@5678",
        "role": Role.ADMIN,
    },
]

DEMO_CASES = [
    {
        "case_number": "FIR-2026-000001",
        "title": "Cybercrime Investigation – Online Fraud Network",
        "description": "Investigation into a multi-state online banking fraud operation targeting senior citizens. Multiple accused identified in Delhi, Mumbai, and Bengaluru.",
        "status": "open",
        "created_by_username": "officer_raj",
    },
    {
        "case_number": "FIR-2026-000002",
        "title": "Digital Forensics – Mobile Device Analysis",
        "description": "Forensic examination of seized digital devices related to an extremist network. Encrypted communications and financial transactions under analysis.",
        "status": "open",
        "created_by_username": "dr_forensics",
    },
    {
        "case_number": "FIR-2026-000003",
        "title": "Evidence Chain Review – Narcotics Trafficking",
        "description": "Chain-of-custody review for evidence submitted in narcotics trafficking case no. SC-2026-7841. Under judicial review.",
        "status": "open",
        "created_by_username": "officer_raj",
    },
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("[OK] Database tables created.")

        created_users = {}

        # Seed users
        for user_data in DEMO_USERS:
            existing = User.query.filter_by(username=user_data["username"]).first()
            if existing:
                print(f"  >> User '{user_data['username']}' already exists - skipping.")
                created_users[user_data["username"]] = existing
                continue

            user = User(
                username=user_data["username"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                role=user_data["role"],
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            db.session.flush()
            created_users[user_data["username"]] = user
            print(f"  [OK] Created user: {user_data['username']} [{Role.LABELS[user_data['role']]}]")

        db.session.commit()

        # Seed demo cases
        for case_data in DEMO_CASES:
            existing = Case.query.filter_by(case_number=case_data["case_number"]).first()
            if existing:
                print(f"  >> Case '{case_data['case_number']}' already exists - skipping.")
                continue

            creator = created_users.get(case_data["created_by_username"])
            if not creator:
                creator = User.query.filter_by(username=case_data["created_by_username"]).first()

            if creator:
                case = Case(
                    case_number=case_data["case_number"],
                    title=case_data["title"],
                    description=case_data["description"],
                    status=case_data["status"],
                    created_by=creator.id,
                )
                db.session.add(case)
                print(f"  [OK] Created case: {case_data['case_number']}")

        db.session.commit()

        print()
        print("=" * 60)
        print("  AEGON Seeding Complete!")
        print("=" * 60)
        print()
        print("  Demo Login Credentials:")
        print()
        for u in DEMO_USERS:
            role_label = Role.LABELS.get(u["role"], u["role"])
            print(f"    Username : {u['username']:<20}  Password : {u['password']:<15}  Role : {role_label}")
        print()
        print("  Start the server: python run.py")
        print("  Open browser   : http://127.0.0.1:5000")
        print()


if __name__ == "__main__":
    seed()
