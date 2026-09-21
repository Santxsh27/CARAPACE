"""Tamper-evident Release Passports for verified, human-approved repairs.

The local implementation uses HMAC-SHA256 so the complete trust flow can be
tested without cloud credentials. Production deployments replace the signer
behind this boundary with Cloud KMS; the passport payload does not change.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from .canonical import canonical_json


SIGNATURE_ALGORITHM = "HMAC-SHA256-LOCAL"


def _signature_payload(passport: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in passport.items()
        if key not in {"integrity_signature", "signature_valid"}
    }


def sign_release_passport(passport: Mapping[str, Any], signing_key: str) -> str:
    if len(signing_key) < 8:
        raise ValueError("release-passport signing key is too short")
    message = canonical_json(_signature_payload(passport)).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def build_release_passport(
    *,
    tenant_id: str,
    case: Mapping[str, Any],
    analysis: Mapping[str, Any],
    approval: Mapping[str, Any],
    signing_key: str,
) -> dict[str, Any]:
    if analysis["verification_status"] != "COUNTERFACTUAL_VERIFIED":
        raise ValueError("only independently verified repairs can receive a passport")
    if analysis["counterfactual_search"]["counterfactual_verdict"] != "MATCH":
        raise ValueError("counterfactual financial contracts must pass")
    if approval["decision"] != "APPROVE":
        raise ValueError("human approval is required")

    evidence = {
        "case_id": case["case_id"],
        "run_id": case["run_id"],
        "contract_id": case["contract_id"],
        "failed_checks": sorted(case["failed_checks"]),
        "analysis_id": analysis["analysis_id"],
        "verification_status": analysis["verification_status"],
        "minimal_interventions": analysis["counterfactual_search"][
            "minimal_interventions"
        ],
        "approval_id": approval["approval_id"],
        "candidate_reference": approval["candidate_reference"],
    }
    evidence_digest = hashlib.sha256(
        canonical_json(evidence).encode("utf-8")
    ).hexdigest()
    passport: dict[str, Any] = {
        "schema_version": "1.0",
        "passport_id": f"passport_{uuid4().hex[:24]}",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "case_id": case["case_id"],
        "run_id": case["run_id"],
        "contract_id": case["contract_id"],
        "analysis_id": analysis["analysis_id"],
        "approval_id": approval["approval_id"],
        "reviewer_id": approval["reviewer_id"],
        "candidate_reference": approval["candidate_reference"],
        "verification_status": analysis["verification_status"],
        "counterfactual_verdict": analysis["counterfactual_search"][
            "counterfactual_verdict"
        ],
        "minimal_interventions": analysis["counterfactual_search"][
            "minimal_interventions"
        ],
        "regression_scenarios": [
            scenario["name"] for scenario in analysis["regression_scenarios"]
        ],
        "ai_provenance": {
            "provider": analysis["provider"],
            "model": analysis["model"],
            "mode": analysis["mode"],
            "ai_authorized_release": False,
        },
        "evidence_digest_sha256": evidence_digest,
        "signature_algorithm": SIGNATURE_ALGORITHM,
    }
    passport["integrity_signature"] = sign_release_passport(passport, signing_key)
    return passport


def verify_release_passport(passport: Mapping[str, Any], signing_key: str) -> bool:
    supplied = str(passport.get("integrity_signature", ""))
    if len(supplied) != 64:
        return False
    expected = sign_release_passport(passport, signing_key)
    return hmac.compare_digest(supplied, expected)
