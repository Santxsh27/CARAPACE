"""Canonicalization shared by PAC producers and deterministic verifiers."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


REQUEST_FIELDS = (
    "amount_minor",
    "currency",
    "direction",
    "fees_minor",
    "payee_id",
    "purpose",
    "reference",
)


def canonical_json(value: Any) -> str:
    """Return stable UTF-8 JSON suitable for hashing and signing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_request(payment: Mapping[str, Any]) -> dict[str, Any]:
    """Select the bank-canonical fields that a customer actually approves."""

    missing = [field for field in REQUEST_FIELDS if field not in payment]
    if missing:
        raise ValueError(f"missing canonical request fields: {', '.join(missing)}")
    return {field: payment[field] for field in REQUEST_FIELDS}


def sha256_hex(value: Any) -> str:
    """Hash a canonical JSON value with SHA-256."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def request_digest(payment: Mapping[str, Any]) -> str:
    """Return the digest bound into a Payment Assurance Contract."""

    return sha256_hex(canonical_request(payment))

