"""Reproducible development comparison, not a real-world fraud benchmark.

Run: python -m carapace_core.operations_benchmark
Both policies share identical financial rules; only evidence acquisition differs.
"""
import json
import tempfile
from pathlib import Path

from carapace_ai.operations import LocalOperationsPlanner
from carapace_api.operations import OperationsService
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.obligations import check_obligation
from carapace_integrations.operations_fixtures import CASES, load_case


def benchmark():
    rows = []
    expected = {"routine": ("POSTED_SYNTHETIC", 48_000_000),
                "partial-credit": ("POSTED_SYNTHETIC", 36_000_000)}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        service = OperationsService(root / "benchmark.db", BankEnvelopeSigner(root / "key.pem", allow_generate=True), LocalOperationsPlanner())
        for case_id in CASES:
            case = load_case(case_id)
            full = check_obligation(case["invoice"], case["records"])
            result = service.resolve("benchmark", case_id)
            status, amount = expected.get(case_id, ("HELD", None))
            actual = result["posting"]["payload"]["amount_minor"] if result["posting"] else None
            rows.append({"case": case_id, "expected": status, "actual": result["status"],
                         "correct": status == result["status"] and amount == actual,
                         "adaptive_lookups": result["lookup_count"], "full_fetch_lookups": 5,
                         "full_fetch_decision": full["decision"], "posted_minor": actual})
    return {"scope": "Six hand-authored synthetic cases; local rule planner, no live model evaluation or held-out corpus.",
            "cases": rows, "correct_cases": sum(row["correct"] for row in rows),
            "total_cases": len(rows), "adaptive_lookups": sum(row["adaptive_lookups"] for row in rows),
            "full_fetch_lookups": sum(row["full_fetch_lookups"] for row in rows)}


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
