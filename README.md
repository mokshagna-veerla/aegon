# AEGON — Secure Digital Evidence Management Platform

> **SIH Problem 26190** · Ministry of Home Affairs / National Crime Records Bureau (NCRB)

A case-centric secure digital document management prototype featuring cryptographic integrity verification, simulated blockchain anchoring, role-based access control (RBAC), and view-only watermarked document inspection.

---

## Features

| Feature | Implementation |
|---|---|
| **SHA-256 Integrity** | Every document hashed on upload, re-hashed on verify |
| **AES-256-GCM Encryption** | All documents encrypted before vault storage |
| **RSA-2048 Signatures** | Server keypair signs each document hash on upload |
| **Blockchain Anchoring** | JSON append-only ledger with tx_hash chaining |
| **Role-Based Access** | 4 roles: Police/IO · Forensic · Legal/Judge · Admin |
| **Watermarked Viewer** | In-memory decrypt → reportlab overlay → PDF.js canvas |
| **OCR Search** | pytesseract extraction with graceful fallback |
| **Tamper Detection** | Byte-flip simulation + AES-GCM tag verification |
| **Screenshot Prevention** | 6-layer: PrtScn nuke, blur-on-blur, getDisplayMedia intercept, canvas poison |
| **Audit Trail** | Every action (upload, view, verify, tamper, login) logged |

---

## Tech Stack

- **Backend**: Python 3.11, Flask (Blueprints), SQLAlchemy ORM
- **Database**: SQLite (prototype) — MySQL-ready via `DATABASE_URL` env var
- **Crypto**: `cryptography` library (AES-256-GCM, RSA-2048 PSS, SHA-256)
- **Document**: `reportlab`, `pypdf`, `pytesseract`, `Pillow`
- **Frontend**: HTML5, Vanilla JS, Tailwind CSS (CDN), PDF.js

---

## Stakeholder Roles

| Role | Upload | View | Verify | Tamper Sim |
|---|---|---|---|---|
| Police / IO | ✅ | ✅ | ✅ | ❌ |
| Forensic Expert | ✅ | ✅ | ✅ | ❌ |
| Legal / Judge | ❌ | ✅ | ✅ | ❌ |
| Administrator | ✅ | ✅ | ✅ | ✅ |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Git

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd aegon

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed database with demo users and cases
python seed_db.py

# Start the Flask development server
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Demo Credentials

| Username | Password | Role |
|---|---|---|
| `officer_raj` | `Pass@1234` | Police / IO |
| `dr_forensics` | `Pass@1234` | Forensic Expert |
| `judge_sharma` | `Pass@1234` | Legal / Judge |
| `admin` | `Admin@5678` | Administrator |

---

## End-to-End Workflow

1. **Login** as `officer_raj` → Create Case → Upload PDF evidence
2. **Verify** integrity → Green "AUTHENTIC" badge (SHA-256 + blockchain match)
3. **Login** as `judge_sharma` → View document → Watermarked PDF-only viewer
4. **Login** as `admin` → Simulate tamper (byte-flip) → Verify → Red "TAMPER DETECTED"
5. **Restore** → Verify again → Green restored

---

## Security Architecture

```
Upload Pipeline:
  Raw File → SHA-256 → RSA-2048 Sign → AES-256-GCM Encrypt → /vault/encrypted/
                                                                      ↓
                              blockchain_ledger.json ← Anchor (tx_hash chained)

Verify Pipeline:
  blockchain_ledger → anchored_hash
  vault decrypt → re-hash SHA-256
  Compare → MATCH ✅ or MISMATCH ❌

View Pipeline:
  AES decrypt (in-memory) → reportlab watermark → pypdf merge → PDF.js canvas
```

---

## Project Structure

```
aegon/
├── app/
│   ├── blueprints/       # auth, cases, documents, verify
│   ├── models/           # User, Case, Document, AuditTrail
│   ├── services/         # crypto, blockchain, ocr, watermark
│   └── templates/        # Jinja2 HTML (Tailwind CDN)
├── requirements.txt
├── seed_db.py
└── run.py
```

---

## Environment Variables (Production)

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret (change in production!) |
| `DATABASE_URL` | e.g. `mysql+pymysql://user:pass@host/aegon` |

---

## License

This prototype was developed for **Smart India Hackathon 2026** (Problem Statement 26190).
Ministry of Home Affairs / National Crime Records Bureau.
