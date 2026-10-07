"""Exercise the real Firestore transaction callback with a strict in-memory driver.

These are contract tests, not a claim of live Firestore integration coverage.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
import unittest

from carapace_api.friday_durable import FirestoreFridayState
import test_financial_friday
from carapace_core.friday_live import FridayMandate, IncomingFinancialSignal


class Snapshot:
    def __init__(self, value):
        self.value = deepcopy(value)
        self.exists = value is not None

    def to_dict(self):
        return deepcopy(self.value)


class Reference:
    def __init__(self, client, path):
        self.client, self.path = client, path
        self.id = path[-1]

    def collection(self, name):
        return Reference(self.client, self.path + (name,))

    def document(self, name):
        return Reference(self.client, self.path + (name,))

    def get(self, transaction=None):
        if transaction and transaction.writes:
            raise AssertionError("Firestore reads must precede writes")
        return Snapshot(self.client.records.get(self.path))

    def set(self, value):
        self.client.records[self.path] = deepcopy(value)


class MemoryClient:
    def __init__(self):
        self.records = {}
        self.lock = RLock()

    def collection(self, name):
        return Reference(self, (name,))


class Transaction:
    def __init__(self):
        self.writes = []

    def set(self, ref, value):
        self.writes.append((ref, deepcopy(value)))


class TransactionalMemory(FirestoreFridayState):
    def __init__(self):
        super().__init__("test", client=MemoryClient())
        self.fail_commit = False

    def _atomic(self, callback):
        with self._client.lock:
            # Simulate an aborted attempt. Only the second attempt commits.
            callback(Transaction())
            transaction = Transaction()
            result = callback(transaction)
            if self.fail_commit:
                raise RuntimeError("injected commit failure")
            for ref, value in transaction.writes:
                ref.set(value)
            return result


class DurableTransactionTests(unittest.TestCase):
    def setUp(self):
        self.base = test_financial_friday.FinancialFridayTests()
        self.base.setUp()
        self.store = TransactionalMemory()
        self.base.service.durable = self.store
        self.service = self.base.service
        self.service.save_mandate("tenant-a", FridayMandate(
            instruction="Handle verified household bills and protect my reserve.",
            protected_balance_minor=1_000_000, automatic_payment_limit_minor=300_000))
        self.base.publish_live_bill()
        self.signal = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="MESSAGE", content_text="TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi"))

    def tearDown(self):
        self.base.tearDown()

    def test_restart_preserves_receipt_balance_and_duplicate_guard(self):
        first = self.service.run_live_signal("tenant-a", self.signal["event_id"])["run"]
        self.assertEqual(first["status"], "COMPLETED_SYNTHETIC")
        from carapace_api.financial_friday import FinancialFridayService
        restored = FinancialFridayService(self.base.path.parent / "restored.db", self.base.signer,
                                          self.service.planner, self.store)
        second = restored.run_live_signal("tenant-a", self.signal["event_id"])["run"]
        self.assertEqual(second["status"], "ALREADY_COMPLETED")
        self.assertEqual(restored.get("tenant-a", first["run_id"])["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(restored.mandate("tenant-a")["sandbox_balance_minor"], 4_750_100)
        restored.save_mandate("tenant-a", FridayMandate(**restored.mandate("tenant-a")["mandate"]))
        self.assertEqual(restored.mandate("tenant-a")["sandbox_balance_minor"], 4_750_100)

    def test_concurrent_runs_create_one_effect(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.service.run_live_signal("tenant-a", self.signal["event_id"])["run"], range(2)))
        self.assertEqual(sum(r["outcome"]["new_payment_created"] for r in results), 1)
        self.assertEqual(self.service.mandate("tenant-a")["sandbox_balance_minor"], 4_750_100)

    def test_provider_changed_is_held(self):
        bill = self.store.get("provider_bills", "tenant-a", "LIVE-1001")
        bill["payee_id"] = "attacker@upi"
        self.store.put("provider_bills", "tenant-a", "LIVE-1001", bill)
        result = self.service.run_live_signal("tenant-a", self.signal["event_id"])["run"]
        self.assertEqual(result["outcome"]["reason"], ["PROVIDER_CHANGED"])
        self.assertEqual(self.service.mandate("tenant-a")["sandbox_balance_minor"], 5_000_000)

    def test_commit_failure_has_no_partial_payment(self):
        self.store.fail_commit = True
        with self.assertRaises(RuntimeError):
            self.service.run_live_signal("tenant-a", self.signal["event_id"])
        self.assertEqual(self.service.mandate("tenant-a")["sandbox_balance_minor"], 5_000_000)
        self.assertFalse(any("payments" in path for path in self.store._client.records))

    def test_different_message_same_bill_does_not_pay_twice(self):
        self.service.run_live_signal("tenant-a", self.signal["event_id"])
        other = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="MESSAGE", content_text="Reminder: TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi"))
        result = self.service.run_live_signal("tenant-a", other["event_id"])["run"]
        self.assertEqual(result["status"], "ALREADY_COMPLETED")

    def test_mandate_change_is_held(self):
        rules = self.service.mandate("tenant-a")["mandate"]
        rules["instruction"] = "Stop and review all new household bill instructions."
        self.service.save_mandate("tenant-a", FridayMandate(**rules))
        result = self.service.run_live_signal("tenant-a", self.signal["event_id"])["run"]
        self.assertEqual(result["outcome"]["reason"], ["MANDATE_CHANGED"])

    def test_automatic_permission_revoked_is_held(self):
        record = self.store.get("signals", "tenant-a", self.signal["event_id"])
        result = self.service.run("tenant-a", record["case_id"], automatic=True)
        self.assertEqual(result["outcome"]["reason"], ["AUTOMATIC_PERMISSION_CHANGED"])

    def test_current_protected_balance_is_enforced(self):
        rules = self.service.mandate("tenant-a")["mandate"]
        rules["protected_balance_minor"] = 4_900_000
        self.service.save_mandate("tenant-a", FridayMandate(**rules))
        result = self.service.run_live_signal("tenant-a", self.signal["event_id"])["run"]
        self.assertEqual(result["outcome"]["reason"], ["PROTECTED_BALANCE"])


if __name__ == "__main__":
    unittest.main()
