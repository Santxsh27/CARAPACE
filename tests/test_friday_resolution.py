from __future__ import annotations

import unittest

from pydantic import ValidationError

from carapace_core.friday_resolution import (
    BankPosting, BillBinding, BillerStatus, ResolutionState, ResolutionTrust, resolve_bill,
)


class BillResolutionTests(unittest.TestCase):
    def setUp(self):
        self.binding = BillBinding(tenant_id="a", biller_id="utility", bill_id="july", payee_id="utility-account", amount_minor=50000, currency="INR")
        self.bank = BankPosting(binding=self.binding, issuer_id="bank", evidence_ref="bank-1", posting_id="posting-1", payment_ref="payment-1", status="SETTLED", observed_at=1000)
        self.biller = BillerStatus(binding=self.binding, issuer_id="utility", evidence_ref="utility-1", status="OVERDUE", observed_at=1000)
        self.trust = ResolutionTrust(bank_issuers=("bank",), biller_issuers=("utility",), checked_at=1001)

    def resolve(self, postings=None, biller=None, trust=None):
        answer = resolve_bill(self.binding, postings if postings is not None else (self.bank,), biller or self.biller, trust or self.trust)
        self.assertFalse(answer.money_movement_permitted)
        return answer

    def test_overdue_settled_proposes_reconciliation_not_payment(self):
        answer = self.resolve()
        self.assertEqual(answer.state, ResolutionState.RECONCILIATION_PROPOSED)
        self.assertEqual(answer.action, "REQUEST_BILLER_RECONCILIATION")
        self.assertFalse(answer.action_permitted)
        self.assertEqual(answer.evidence_refs, ("bank-1", "utility-1"))

    def test_explicit_permission_and_fresh_evidence_allow_request_only(self):
        answer = self.resolve(trust=self.trust.model_copy(update={"reconciliation_permitted": True}))
        self.assertEqual(answer.state, ResolutionState.RECONCILIATION_READY)
        self.assertTrue(answer.action_permitted)

    def test_permission_cannot_override_new_contradiction(self):
        permission = self.trust.model_copy(update={"reconciliation_permitted": True})
        wrong = self.biller.model_copy(update={"payment_ref": "different"})
        self.assertEqual(self.resolve(biller=wrong, trust=permission).state, ResolutionState.HOLD)

    def test_confirmed_requires_provider_payment_link(self):
        paid = self.biller.model_copy(update={"status": "PAID", "payment_ref": "payment-1"})
        answer = self.resolve(biller=paid)
        self.assertEqual(answer.state, ResolutionState.CONFIRMED)
        self.assertIsNone(answer.action)
        self.assertEqual(self.resolve(biller=paid.model_copy(update={"payment_ref": None})).state, ResolutionState.UNVERIFIED)

    def test_pending_and_unknown_never_repay(self):
        for status in ("PENDING", "UNKNOWN"):
            with self.subTest(status=status):
                answer = self.resolve(postings=(self.bank.model_copy(update={"status": status}),))
                self.assertEqual(answer.state, ResolutionState.PENDING)
                self.assertIsNone(answer.action)

    def test_pending_second_attempt_prevents_premature_resolution(self):
        pending = self.bank.model_copy(update={"status": "PENDING", "posting_id": "p2", "evidence_ref": "b2", "payment_ref": "attempt2"})
        self.assertEqual(self.resolve(postings=(self.bank, pending)).state, ResolutionState.PENDING)

    def test_distinct_duplicate_debits_require_review_not_refund(self):
        second = self.bank.model_copy(update={"posting_id": "p2", "evidence_ref": "b2"})
        answer = self.resolve(postings=(self.bank, second))
        self.assertEqual(answer.state, ResolutionState.REVIEW_DUPLICATE)
        self.assertIsNone(answer.action)

    def test_repeated_evidence_is_not_a_second_debit(self):
        self.assertEqual(self.resolve(postings=(self.bank, self.bank)).state, ResolutionState.HOLD)
        repeated = self.bank.model_copy(update={"evidence_ref": "b2", "status": "REVERSED"})
        self.assertEqual(self.resolve(postings=(self.bank, repeated)).reason, "REPEATED_OR_CONFLICTING_POSTING")

    def test_failed_or_reversed_does_not_authorize_replacement(self):
        for status in ("FAILED", "REVERSED"):
            answer = self.resolve(postings=(self.bank.model_copy(update={"status": status}),))
            self.assertEqual(answer.state, ResolutionState.UNVERIFIED)
            self.assertIsNone(answer.action)

    def test_conflicting_settlement_and_reversal_are_not_resolved(self):
        reversed_posting = self.bank.model_copy(update={"posting_id": "p2", "evidence_ref": "b2", "status": "REVERSED"})
        self.assertEqual(self.resolve(postings=(self.bank, reversed_posting)).reason, "CONFLICTING_FINAL_PAYMENT_STATUS")

    def test_failed_distinct_attempt_does_not_erase_settled_payment(self):
        failed_attempt = self.bank.model_copy(update={"posting_id": "p2", "evidence_ref": "b2", "status": "FAILED", "payment_ref": "different-attempt"})
        self.assertEqual(self.resolve(postings=(self.bank, failed_attempt)).state, ResolutionState.RECONCILIATION_PROPOSED)

    def test_all_binding_fields_are_enforced_for_each_provider(self):
        for field, value in (("tenant_id", "b"), ("biller_id", "other"), ("bill_id", "august"), ("payee_id", "attacker"), ("amount_minor", 1), ("currency", "USD")):
            changed = self.binding.model_copy(update={field: value})
            with self.subTest(field=field, provider="bank"):
                self.assertEqual(self.resolve(postings=(self.bank.model_copy(update={"binding": changed}),)).state, ResolutionState.HOLD)
            with self.subTest(field=field, provider="biller"):
                self.assertEqual(self.resolve(biller=self.biller.model_copy(update={"binding": changed})).state, ResolutionState.HOLD)

    def test_trust_is_required_for_both_issuers(self):
        self.assertEqual(self.resolve(postings=(self.bank.model_copy(update={"issuer_id": "fake"}),)).state, ResolutionState.UNVERIFIED)
        self.assertEqual(self.resolve(biller=self.biller.model_copy(update={"issuer_id": "fake"})).state, ResolutionState.UNVERIFIED)

    def test_expired_and_future_evidence_are_not_permissions(self):
        for observed_at in (0, 2000):
            with self.subTest(observed_at=observed_at):
                answer = self.resolve(postings=(self.bank.model_copy(update={"observed_at": observed_at}),), trust=self.trust.model_copy(update={"reconciliation_permitted": True}))
                self.assertEqual(answer.state, ResolutionState.UNVERIFIED)
                self.assertFalse(answer.action_permitted)
                self.assertEqual(self.resolve(biller=self.biller.model_copy(update={"observed_at": observed_at})).state, ResolutionState.UNVERIFIED)

    def test_missing_evidence_and_unknown_biller(self):
        self.assertEqual(resolve_bill(self.binding, (self.bank,), None, self.trust).state, ResolutionState.UNVERIFIED)
        self.assertEqual(self.resolve(postings=()).state, ResolutionState.UNVERIFIED)
        self.assertEqual(self.resolve(biller=self.biller.model_copy(update={"status": "UNKNOWN"})).state, ResolutionState.UNVERIFIED)

    def test_strict_models_reject_coercion_invalid_values_and_extra_ai_fields(self):
        for amount in (0, -1, True, 1.5, "50000"):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                BillBinding.model_validate({**self.binding.model_dump(), "amount_minor": amount})
        with self.assertRaises(ValidationError):
            BankPosting.model_validate({**self.bank.model_dump(), "execute_refund": True})
        with self.assertRaises(ValidationError):
            ResolutionTrust.model_validate({**self.trust.model_dump(), "reconciliation_permitted": "yes"})
        with self.assertRaises(ValidationError):
            BankPosting.model_validate({**self.bank.model_dump(), "status": "SAFE"})


if __name__ == "__main__":
    unittest.main()
