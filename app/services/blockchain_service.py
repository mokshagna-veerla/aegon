"""Simulated blockchain ledger service.

Emulates an Ethereum smart contract interface:
  - recordDocument(...)  →  append entry to JSON ledger
  - getDocumentRecord(doc_id)  →  read anchored record

Each ledger entry includes a tx_hash (SHA-256 of its contents) to make
the append-only chain tamper-evident for the prototype.

Ledger file: blockchain_ledger.json (root of project)
"""
import hashlib
import json
import os
from datetime import datetime, timezone


def _load_ledger(ledger_path: str) -> list[dict]:
    if not os.path.exists(ledger_path):
        return []
    with open(ledger_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_ledger(ledger_path: str, ledger: list[dict]) -> None:
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


def _compute_tx_hash(entry: dict) -> str:
    """Deterministic hash of a ledger entry (excluding tx_hash field)."""
    payload = json.dumps(
        {k: v for k, v in entry.items() if k != "tx_hash"},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Public interface (emulates Ethereum smart contract methods)
# ---------------------------------------------------------------------------

def record_document(
    ledger_path: str,
    doc_id: int,
    case_id: int,
    sha256_hash: str,
    digital_signature: str,
    uploader_username: str,
    filename: str,
) -> str:
    """recordDocument – anchor document metadata to the ledger.

    Returns the transaction hash (tx_hash) of the new block entry.
    """
    ledger = _load_ledger(ledger_path)

    entry: dict = {
        "block_index": len(ledger),
        "doc_id": doc_id,
        "case_id": case_id,
        "filename": filename,
        "sha256_hash": sha256_hash,
        "digital_signature": digital_signature[:64] + "...",  # truncated for readability
        "uploader": uploader_username,
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "tx_hash": "",  # computed below
    }
    entry["tx_hash"] = _compute_tx_hash(entry)

    # Chain integrity: include previous tx_hash
    if ledger:
        entry["prev_tx_hash"] = ledger[-1]["tx_hash"]
    else:
        entry["prev_tx_hash"] = "0" * 64  # genesis block

    # Recompute with prev_tx_hash included
    entry["tx_hash"] = _compute_tx_hash(entry)

    ledger.append(entry)
    _save_ledger(ledger_path, ledger)

    return entry["tx_hash"]


def get_document_record(ledger_path: str, doc_id: int) -> dict | None:
    """getDocumentRecord – retrieve anchored record for a document ID."""
    ledger = _load_ledger(ledger_path)
    for entry in reversed(ledger):  # most recent first
        if entry.get("doc_id") == doc_id:
            return entry
    return None


def get_all_records(ledger_path: str) -> list[dict]:
    """Return the full ledger (newest first)."""
    ledger = _load_ledger(ledger_path)
    return list(reversed(ledger))
