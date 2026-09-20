"""Deterministic UPI MDR policy checks for CARAPACE FeeShield.

The policy is kept separate from AI reasoning. Production deployments must
version and approve the applicable NPCI/bank policy before enabling it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


POLICY_VERSION = "india-upi-mdr-2026-10-15-v1"
EFFECTIVE_ON = date(2026, 10, 15)
THRESHOLD_MINOR = 200_000  # INR 2,000 in paise
STANDARD_CAP_MINOR = 30_000  # INR 300 in paise
SMALL_MERCHANT_MONTHLY_LIMIT_MINOR = 10_000_000  # INR 1 lakh


class UpiPaymentKind(StrEnum):
    P2P = "P2P"
    P2M = "P2M"
    P2PM = "P2PM"


class MerchantSector(StrEnum):
    STANDARD = "STANDARD"
    ESSENTIAL = "ESSENTIAL"
    CAPITAL_MARKET = "CAPITAL_MARKET"


@dataclass(frozen=True)
class FeeAssessment:
    policy_version: str
    expected_mdr_minor: int
    customer_mdr_surcharge_minor: int
    customer_protected: bool
    merchant_settlement_matches: bool | None
    violations: tuple[str, ...]
    explanation: str

    @property
    def verdict(self) -> str:
        return "COMPLIANT" if not self.violations else "VIOLATION"

    def as_dict(self) -> dict[str, object]:
        return {**asdict(self), "verdict": self.verdict}


def _basis_points(amount_minor: int, points: int) -> int:
    return int(
        (Decimal(amount_minor) * Decimal(points) / Decimal(10_000)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def expected_upi_mdr_minor(
    *,
    amount_minor: int,
    initiated_on: date,
    payment_kind: UpiPaymentKind,
    sector: MerchantSector = MerchantSector.STANDARD,
    merchant_monthly_upi_minor: int | None = None,
) -> tuple[int, str]:
    """Calculate merchant-side MDR in paise under the versioned policy."""

    if amount_minor <= 0:
        raise ValueError("amount_minor must be positive")
    if initiated_on < EFFECTIVE_ON:
        return 0, "The new MDR policy is not effective for this payment date."
    if payment_kind == UpiPaymentKind.P2P:
        return 0, "Person-to-person UPI remains free at every amount."
    if (
        payment_kind == UpiPaymentKind.P2PM
        and merchant_monthly_upi_minor is not None
        and merchant_monthly_upi_minor <= SMALL_MERCHANT_MONTHLY_LIMIT_MINOR
    ):
        return 0, "Eligible small P2PM merchants remain under zero MDR."
    if amount_minor <= THRESHOLD_MINOR:
        return 0, "Merchant payments up to INR 2,000 remain free."
    if sector == MerchantSector.ESSENTIAL:
        return 500, "Essential and thin-margin sectors use a flat INR 5 MDR."
    if sector == MerchantSector.CAPITAL_MARKET:
        return min(_basis_points(amount_minor, 2), STANDARD_CAP_MINOR), (
            "Capital-market payments use 0.02% MDR, capped at INR 300."
        )
    return min(_basis_points(amount_minor, 40), STANDARD_CAP_MINOR), (
        "Eligible merchant payments use 0.4% MDR, capped at INR 300."
    )


def assess_upi_charge(
    *,
    amount_minor: int,
    initiated_on: date,
    payment_kind: UpiPaymentKind,
    customer_mdr_surcharge_minor: int,
    actual_merchant_mdr_minor: int | None = None,
    sector: MerchantSector = MerchantSector.STANDARD,
    merchant_monthly_upi_minor: int | None = None,
) -> FeeAssessment:
    """Check both customer protection and merchant settlement evidence."""

    if customer_mdr_surcharge_minor < 0:
        raise ValueError("customer_mdr_surcharge_minor cannot be negative")
    expected, explanation = expected_upi_mdr_minor(
        amount_minor=amount_minor,
        initiated_on=initiated_on,
        payment_kind=payment_kind,
        sector=sector,
        merchant_monthly_upi_minor=merchant_monthly_upi_minor,
    )
    violations: list[str] = []
    if customer_mdr_surcharge_minor:
        violations.append("CUSTOMER_MDR_SURCHARGE_PROHIBITED")
    merchant_matches = (
        None
        if actual_merchant_mdr_minor is None
        else actual_merchant_mdr_minor == expected
    )
    if merchant_matches is False:
        violations.append("MERCHANT_MDR_SETTLEMENT_MISMATCH")
    return FeeAssessment(
        policy_version=POLICY_VERSION,
        expected_mdr_minor=expected,
        customer_mdr_surcharge_minor=customer_mdr_surcharge_minor,
        customer_protected=customer_mdr_surcharge_minor == 0,
        merchant_settlement_matches=merchant_matches,
        violations=tuple(violations),
        explanation=explanation,
    )
