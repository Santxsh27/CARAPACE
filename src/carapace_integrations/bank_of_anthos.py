"""Adapter for the official Bank of Anthos append-only PostgreSQL ledger.

The upstream ledger stores a financial transaction, but it does not persist the
request UUID used by LedgerWriter. For that reason this module requires a
trusted, explicit binding from returned ledger transaction IDs to a CARAPACE
contract. It never guesses that relationship from amount, account, or time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

import psycopg


LOCAL_ROUTING_NUMBER = "883745000"


@dataclass(frozen=True)
class BankOfAnthosTransaction:
    transaction_id: int
    from_account: str
    to_account: str
    from_routing: str
    to_routing: str
    amount_minor: int
    timestamp: datetime

    @classmethod
    def from_row(cls, row: Sequence[Any]) -> "BankOfAnthosTransaction":
        return cls(
            transaction_id=int(row[0]),
            from_account=str(row[1]).strip(),
            to_account=str(row[2]).strip(),
            from_routing=str(row[3]).strip(),
            to_routing=str(row[4]).strip(),
            amount_minor=int(row[5]),
            timestamp=row[6],
        )

    def as_debit_evidence(
        self, *, contract_id: str, currency: str
    ) -> dict[str, Any]:
        """Map one authoritative ledger row to one payer-side debit effect."""

        return {
            "entry_id": f"boa:transaction:{self.transaction_id}",
            "logical_payment_id": contract_id,
            "account_ref": self.from_account,
            "counterparty_ref": self.to_account,
            "direction": "DEBIT",
            "amount_minor": self.amount_minor,
            "currency": currency,
            "status": "POSTED",
        }

    def as_public_record(self) -> dict[str, Any]:
        """Return the exact non-secret ledger fields used by the local explorer."""

        timestamp = self.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return {
            "transaction_id": self.transaction_id,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "from_routing": self.from_routing,
            "to_routing": self.to_routing,
            "amount_minor": self.amount_minor,
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
        }


def _validate_identifier(value: str, expected_length: int, label: str) -> None:
    if len(value) != expected_length or not value.isdigit():
        raise ValueError(f"{label} must be exactly {expected_length} digits")


class BankOfAnthosLedger:
    """Small integration boundary around Bank of Anthos's TRANSACTIONS table."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def wait_until_ready(self, timeout_seconds: float = 60) -> None:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with psycopg.connect(
                    self._database_url, connect_timeout=3
                ) as connection:
                    table = connection.execute(
                        "SELECT to_regclass('public.transactions')"
                    ).fetchone()
                    if table and table[0] == "transactions":
                        return
            except psycopg.Error as error:
                last_error = error
            time.sleep(1)
        raise RuntimeError(
            "Bank of Anthos ledger did not become ready within the timeout"
        ) from last_error

    def is_ready(self) -> bool:
        try:
            self.wait_until_ready(timeout_seconds=1)
        except RuntimeError:
            return False
        return True

    def insert_controlled_test_transaction(
        self,
        *,
        from_account: str,
        to_account: str,
        amount_minor: int,
        from_routing: str = LOCAL_ROUTING_NUMBER,
        to_routing: str = LOCAL_ROUTING_NUMBER,
    ) -> int:
        """Insert artificial money for the local test harness only.

        A production CARAPACE deployment must use a read-only ledger adapter or
        trusted processor events. CARAPACE itself never calls this method while
        observing real funds.
        """

        _validate_identifier(from_account, 10, "from_account")
        _validate_identifier(to_account, 10, "to_account")
        _validate_identifier(from_routing, 9, "from_routing")
        _validate_identifier(to_routing, 9, "to_routing")
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")

        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO transactions (
                    from_acct, to_acct, from_route, to_route, amount, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING transaction_id
                """,
                (
                    from_account,
                    to_account,
                    from_routing,
                    to_routing,
                    amount_minor,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                ),
            ).fetchone()
            if row is None:
                raise RuntimeError("Bank of Anthos did not return a transaction ID")
            return int(row[0])

    def fetch_bound_transactions(
        self, transaction_ids: Sequence[int]
    ) -> list[BankOfAnthosTransaction]:
        """Read only explicitly bound transaction IDs from the authoritative ledger."""

        if not transaction_ids:
            raise ValueError("at least one transaction ID is required")
        unique_ids = list(dict.fromkeys(int(value) for value in transaction_ids))
        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, from_acct, to_acct, from_route,
                       to_route, amount, timestamp
                FROM transactions
                WHERE transaction_id = ANY(%s)
                ORDER BY transaction_id
                """,
                (unique_ids,),
            ).fetchall()
        if len(rows) != len(unique_ids):
            found = {int(row[0]) for row in rows}
            missing = sorted(set(unique_ids) - found)
            raise RuntimeError(f"bound ledger transactions are missing: {missing}")
        return [BankOfAnthosTransaction.from_row(row) for row in rows]

    def fetch_recent_transactions(
        self, limit: int = 20
    ) -> list[BankOfAnthosTransaction]:
        """Read recent authoritative rows for the beginner-facing data explorer."""

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, from_acct, to_acct, from_route,
                       to_route, amount, timestamp
                FROM transactions
                ORDER BY transaction_id DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [BankOfAnthosTransaction.from_row(row) for row in rows]
