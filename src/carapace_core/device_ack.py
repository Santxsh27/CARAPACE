"""Browser P-256 acknowledgement of an exact bank-issued payment statement.

This verifies control of an enrolled development key. It cannot establish that
the key's user actually saw, read, understood, or freely accepted the screen.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from .canonical import canonical_json, sha256_hex


def device_key_fingerprint(public_key_spki_base64: str) -> str:
    raw = base64.b64decode(public_key_spki_base64, validate=True)
    if len(raw) > 256:
        raise ValueError("device public key is too large")
    key = serialization.load_der_public_key(raw)
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("device key must be P-256")
    return hashlib.sha256(raw).hexdigest()


def build_device_statement(
    envelope: Mapping[str, Any], decision: Mapping[str, Any],
    *, choice: str, device_id: str, device_key_sha256: str,
) -> dict[str, Any]:
    if choice not in {"PROCEED", "CANCEL"}:
        raise ValueError("unsupported customer choice")
    return {
        "schema_version": "carapace-device-statement-1",
        "tenant_id": envelope["tenant_id"],
        "order_id": envelope["order_id"],
        "decision_id": decision["decision_id"],
        "decision_receipt_id": decision["protection_receipt_id"],
        "bank_order_sha256": sha256_hex(envelope),
        "bank_order_signature": decision["envelope_signature"],
        "order_nonce": envelope["nonce"],
        "amount_minor": envelope["amount_minor"],
        "currency": envelope["currency"],
        "direction": envelope["direction"],
        "payee_display_name": envelope["payee_display_name"],
        "payee_account_last4": envelope["payee_account"][-4:],
        "verdict": decision["verdict"],
        "exact_warning": decision["customer_message"],
        "choice": choice,
        "device_id": device_id,
        "device_key_sha256": device_key_sha256,
    }


def verify_device_signature(
    statement_json: str, signature_base64: str, public_key_spki_base64: str
) -> bool:
    """WebCrypto ECDSA signatures are 64-byte IEEE-P1363 r||s, not DER."""
    try:
        if canonical_json(json.loads(statement_json)) != statement_json:
            return False
        signature = base64.b64decode(signature_base64, validate=True)
        if len(signature) != 64:
            return False
        raw_key = base64.b64decode(public_key_spki_base64, validate=True)
        key = serialization.load_der_public_key(raw_key)
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            return False
        r = int.from_bytes(signature[:32], "big")
        s = int.from_bytes(signature[32:], "big")
        key.verify(
            encode_dss_signature(r, s), statement_json.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (ValueError, TypeError, binascii.Error, InvalidSignature, UnsupportedAlgorithm, UnicodeError):
        return False
