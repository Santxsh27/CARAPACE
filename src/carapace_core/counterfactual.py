"""Minimal counterfactual repair search for failed payment evidence.

This module never changes a real ledger. It applies a small allowlist of safe,
deterministic transformations to an isolated evidence copy and asks the normal
financial verifier whether the violated contracts would then pass.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable, Mapping

from .canonical import request_digest
from .verifier import verify_payment


ALLOWED_INTERVENTIONS = (
    "DEDUPLICATE_LOGICAL_DEBITS",
    "REUSE_CONTRACT_IDEMPOTENCY_KEY",
    "RESTORE_BOUND_PAYMENT_REQUEST",
)


@dataclass(frozen=True)
class CounterfactualSearchResult:
    original_verdict: str
    counterfactual_verdict: str
    minimal_interventions: tuple[str, ...]
    experiments_run: int
    remaining_failed_checks: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_verdict": self.original_verdict,
            "counterfactual_verdict": self.counterfactual_verdict,
            "minimal_interventions": list(self.minimal_interventions),
            "experiments_run": self.experiments_run,
            "remaining_failed_checks": list(self.remaining_failed_checks),
        }


def _apply_intervention(
    evidence: dict[str, Any], contract: Mapping[str, Any], intervention: str
) -> None:
    if intervention == "DEDUPLICATE_LOGICAL_DEBITS":
        seen: set[str] = set()
        retained: list[dict[str, Any]] = []
        for entry in evidence.get("ledger_entries", []):
            is_posted_debit = (
                entry.get("direction") == "DEBIT" and entry.get("status") == "POSTED"
            )
            logical_id = str(entry.get("logical_payment_id", ""))
            if is_posted_debit and logical_id in seen:
                continue
            if is_posted_debit:
                seen.add(logical_id)
            retained.append(entry)
        evidence["ledger_entries"] = retained
        return

    if intervention == "REUSE_CONTRACT_IDEMPOTENCY_KEY":
        evidence["idempotency_key"] = contract["integrity"]["idempotency_key"]
        return

    if intervention == "RESTORE_BOUND_PAYMENT_REQUEST":
        payment = contract["payment"]
        actual_request = {
            key: payment[key]
            for key in (
                "direction",
                "amount_minor",
                "currency",
                "fees_minor",
                "payee_id",
                "purpose",
                "reference",
            )
        }
        evidence["actual_request"] = actual_request
        evidence["actual_request_hash_sha256"] = request_digest(actual_request)
        return

    raise ValueError(f"unsupported counterfactual intervention: {intervention}")


def search_minimal_repair(
    contract: Mapping[str, Any],
    evidence: Mapping[str, Any],
    preferred_interventions: Iterable[str] = (),
) -> CounterfactualSearchResult:
    """Find the smallest allowlisted intervention set that restores all invariants."""

    original = verify_payment(contract, evidence)
    if original.passed:
        return CounterfactualSearchResult(
            original_verdict=original.verdict,
            counterfactual_verdict=original.verdict,
            minimal_interventions=(),
            experiments_run=0,
            remaining_failed_checks=(),
        )

    preferred = [item for item in preferred_interventions if item in ALLOWED_INTERVENTIONS]
    ordered = tuple(dict.fromkeys([*preferred, *ALLOWED_INTERVENTIONS]))
    experiments_run = 0
    last_report = original

    for size in range(1, len(ordered) + 1):
        for intervention_set in combinations(ordered, size):
            candidate = deepcopy(dict(evidence))
            for intervention in intervention_set:
                _apply_intervention(candidate, contract, intervention)
            experiments_run += 1
            last_report = verify_payment(contract, candidate)
            if last_report.passed:
                return CounterfactualSearchResult(
                    original_verdict=original.verdict,
                    counterfactual_verdict=last_report.verdict,
                    minimal_interventions=intervention_set,
                    experiments_run=experiments_run,
                    remaining_failed_checks=(),
                )

    return CounterfactualSearchResult(
        original_verdict=original.verdict,
        counterfactual_verdict=last_report.verdict,
        minimal_interventions=(),
        experiments_run=experiments_run,
        remaining_failed_checks=tuple(
            check.code for check in last_report.checks if not check.passed
        ),
    )
