from __future__ import annotations

import unittest
from datetime import date

from carapace_core.fee_policy import (
    MerchantSector,
    UpiPaymentKind,
    assess_upi_charge,
    expected_upi_mdr_minor,
)


EFFECTIVE_DATE = date(2026, 10, 15)


class FeeShieldPolicyTests(unittest.TestCase):
    def expected(self, amount_minor: int, **overrides: object) -> int:
        values = {
            "amount_minor": amount_minor,
            "initiated_on": EFFECTIVE_DATE,
            "payment_kind": UpiPaymentKind.P2M,
        }
        values.update(overrides)
        return expected_upi_mdr_minor(**values)[0]  # type: ignore[arg-type]

    def test_p2p_is_free_at_any_amount(self) -> None:
        self.assertEqual(
            self.expected(10_000_000, payment_kind=UpiPaymentKind.P2P), 0
        )

    def test_p2m_up_to_two_thousand_is_free(self) -> None:
        self.assertEqual(self.expected(200_000), 0)

    def test_standard_p2m_uses_point_four_percent(self) -> None:
        self.assertEqual(self.expected(1_000_000), 4_000)

    def test_standard_p2m_is_capped_at_three_hundred_rupees(self) -> None:
        self.assertEqual(self.expected(10_000_000), 30_000)

    def test_essential_sector_uses_five_rupee_flat_fee(self) -> None:
        self.assertEqual(
            self.expected(500_000, sector=MerchantSector.ESSENTIAL), 500
        )

    def test_capital_market_uses_two_basis_points(self) -> None:
        self.assertEqual(
            self.expected(10_000_000, sector=MerchantSector.CAPITAL_MARKET),
            2_000,
        )

    def test_eligible_small_p2pm_merchant_remains_free(self) -> None:
        self.assertEqual(
            self.expected(
                500_000,
                payment_kind=UpiPaymentKind.P2PM,
                merchant_monthly_upi_minor=10_000_000,
            ),
            0,
        )

    def test_hidden_customer_surcharge_is_a_violation(self) -> None:
        assessment = assess_upi_charge(
            amount_minor=1_000_000,
            initiated_on=EFFECTIVE_DATE,
            payment_kind=UpiPaymentKind.P2M,
            customer_mdr_surcharge_minor=4_000,
            actual_merchant_mdr_minor=4_000,
        )
        self.assertEqual(assessment.verdict, "VIOLATION")
        self.assertIn("CUSTOMER_MDR_SURCHARGE_PROHIBITED", assessment.violations)

    def test_wrong_processor_deduction_is_a_violation(self) -> None:
        assessment = assess_upi_charge(
            amount_minor=500_000,
            initiated_on=EFFECTIVE_DATE,
            payment_kind=UpiPaymentKind.P2M,
            customer_mdr_surcharge_minor=0,
            actual_merchant_mdr_minor=3_000,
        )
        self.assertIn("MERCHANT_MDR_SETTLEMENT_MISMATCH", assessment.violations)


if __name__ == "__main__":
    unittest.main()
