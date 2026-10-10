"""Independent exhaustive oracle and non-execution checks for bill planning."""
from copy import deepcopy
from itertools import combinations
import random
import unittest

from carapace_core.friday_bill_plan import plan_bills


def snapshot(amounts, budget=1000, dates=None):
    return {"scope": "ARTIFICIAL_MONEY", "currency": "INR",
            "available_above_reserve_minor": budget, "automatic_payment_limit_minor": 100000,
            "coverage": {"may_be_truncated": False}, "bills": [
                {"bill_reference": f"BILL-{i:04d}", "provider_id": "power-test",
                 "provider_name": "Artificial power", "payee_id": "power@upi",
                 "amount_minor": amount, "due_date": (dates or ["2026-10-12"]*len(amounts))[i],
                 "currency": "INR", "status": "UNPAID_RECORD"}
                for i, amount in enumerate(amounts)]}


class BillPlanTests(unittest.TestCase):
    def test_beats_expensive_first_greedy_without_spending(self):
        data = snapshot([800, 500, 500])
        before = deepcopy(data)
        plan = plan_bills(data)
        self.assertEqual([b["amount_minor"] for b in plan["selected"]], [500, 500])
        self.assertEqual(plan["planned_total_minor"], 1000)
        self.assertFalse(plan["money_moved"])
        self.assertFalse(plan["payment_authorized"])
        self.assertEqual(data, before)

    def test_earlier_deadline_precedes_count_of_later_bills(self):
        plan = plan_bills(snapshot([800, 500, 500], dates=["2026-10-11", "2026-10-12", "2026-10-12"]))
        self.assertEqual([b["amount_minor"] for b in plan["selected"]], [800])

    def test_exact_solver_matches_independent_exhaustive_oracle(self):
        rng = random.Random(1010)
        for _ in range(80):
            data = snapshot([rng.randint(1, 1200) for _ in range(8)], budget=rng.randint(0, 4000),
                            dates=[f"2026-10-{rng.randint(11,14)}" for _ in range(8)])
            bills = data["bills"]
            dates = sorted({b["due_date"] for b in bills})
            def objective(rows):
                return tuple(sum(b["due_date"] == d for b in rows) for d in dates) + (-sum(b["amount_minor"] for b in rows),)
            feasible = [rows for n in range(9) for rows in combinations(bills, n)
                        if sum(b["amount_minor"] for b in rows) <= data["available_above_reserve_minor"]]
            best = max(objective(rows) for rows in feasible)
            plan = plan_bills(data)
            self.assertEqual(objective(plan["selected"]), best)
            self.assertGreaterEqual(plan["remaining_above_reserve_minor"], 0)

    def test_conflicts_increases_limits_and_paid_excluded(self):
        data = snapshot([100, 200, 300, 400])
        data["automatic_payment_limit_minor"] = 250
        data["bills"][0]["status"] = "RECORDED_PAID"
        data["bills"][1]["status"] = "RECEIPT_CONFLICT"
        data["bills"][2]["status"] = "REVIEW_INCREASE"
        plan = plan_bills(data)
        self.assertFalse(plan["selected"])
        self.assertEqual(len(plan["review"]), 3)
        self.assertEqual(len(plan["already_recorded"]), 1)

    def test_incomplete_or_ambiguous_records_never_return_a_plan(self):
        data = snapshot([100])
        data["coverage"]["may_be_truncated"] = True
        self.assertEqual(plan_bills(data)["state"], "INCOMPLETE_RECORDS")
        data["coverage"]["may_be_truncated"] = False
        data["bills"].append(deepcopy(data["bills"][0]))
        self.assertEqual(plan_bills(data)["state"], "AMBIGUOUS_RECORDS")

    def test_bounded_search_and_invalid_financial_inputs_fail_closed(self):
        self.assertEqual(plan_bills(snapshot([1, 2]), max_bills=1)["state"], "PLANNING_LIMIT")
        self.assertEqual(plan_bills(snapshot([1, 2]), max_states=1)["state"], "PLANNING_LIMIT")
        for value in (-1, True, 1.5, None):
            data = snapshot([100]); data["available_above_reserve_minor"] = value
            with self.assertRaises(ValueError):
                plan_bills(data)
        data = snapshot([100]); data["bills"][0]["due_date"] = "2026-02-30"
        self.assertEqual(plan_bills(data)["review"][0]["reason"], "INVALID_DUE_DATE")
