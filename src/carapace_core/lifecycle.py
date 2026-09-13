"""Deterministic Payment Assurance Contract lifecycle validation."""

from __future__ import annotations

from typing import Iterable


ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"USER_CONFIRMED"}),
    "USER_CONFIRMED": frozenset({"AUTHORIZED", "FAILED"}),
    "AUTHORIZED": frozenset({"SUBMITTED", "FAILED"}),
    "SUBMITTED": frozenset({"ACCEPTED", "FAILED"}),
    "ACCEPTED": frozenset({"SETTLED", "FAILED", "REVERSED"}),
    "SETTLED": frozenset({"REVERSED"}),
    "FAILED": frozenset(),
    "REVERSED": frozenset(),
}


def invalid_transitions(states: Iterable[str]) -> list[str]:
    """Describe unknown states and illegal adjacent transitions."""

    sequence = list(states)
    errors: list[str] = []
    if not sequence:
        return ["lifecycle is empty"]
    if sequence[0] != "DRAFT":
        errors.append(f"lifecycle must start at DRAFT, got {sequence[0]}")

    for state in sequence:
        if state not in ALLOWED_TRANSITIONS:
            errors.append(f"unknown lifecycle state: {state}")

    for current, following in zip(sequence, sequence[1:]):
        if current in ALLOWED_TRANSITIONS and following not in ALLOWED_TRANSITIONS[current]:
            errors.append(f"illegal lifecycle transition: {current} -> {following}")
    return errors

