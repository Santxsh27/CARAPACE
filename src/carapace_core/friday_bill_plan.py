"""Read-only, reserve-constrained planning. Never produces executable programs.

Exact Pareto-frontier dynamic programming prioritises the number of bills on
earlier due dates, then lower spend for ties. It uses no risk score or model
arithmetic. Limits fail closed rather than silently using a greedy substitute.
"""
from datetime import date

from .canonical import sha256_hex


def plan_bills(snapshot: dict, *, max_bills: int = 32, max_states: int = 10000) -> dict:
    if snapshot.get("scope") != "ARTIFICIAL_MONEY" or snapshot.get("currency") != "INR":
        raise ValueError("Only the artificial INR workspace is supported")
    available = snapshot.get("available_above_reserve_minor")
    limit = snapshot.get("automatic_payment_limit_minor")
    if any(type(v) is not int or v < 0 for v in (available, limit)):
        raise ValueError("Exact nonnegative planning limits are required")
    result = {
        "scope": "ARTIFICIAL_MONEY", "read_only": True, "money_moved": False,
        "payment_authorized": False, "currency": "INR", "state": "PLANNED",
        "method": "EXACT_DEADLINE_PARETO_DP", "available_minor": available,
        "selected": [], "deferred": [], "review": [], "already_recorded": [],
        "planned_total_minor": 0, "remaining_above_reserve_minor": available,
        "objective": "Maximise bill count on earliest due dates first; minimise spend for ties.",
        "snapshot_sha256": sha256_hex(snapshot),
        "limits": ["Artificial records only; external payment status is unknown.",
                   "Preview is not a payment, reservation, or permission. Each action must be rechecked.",
                   "Due date is the only priority signal; fees, service criticality and other accounts are not modelled."],
    }
    if snapshot.get("coverage", {}).get("may_be_truncated"):
        result["state"] = "INCOMPLETE_RECORDS"
        return result
    candidates, identities = [], set()
    for raw in snapshot.get("bills", []):
        row = {k: raw.get(k) for k in ("bill_reference", "provider_id", "provider_name", "payee_id", "amount_minor", "due_date")}
        identity = (row["provider_id"], row["bill_reference"])
        if identity in identities or not all(isinstance(row[k], str) and row[k] for k in ("provider_id", "bill_reference", "payee_id")):
            result["state"] = "AMBIGUOUS_RECORDS"
            return result
        identities.add(identity)
        if raw.get("status") == "RECORDED_PAID":
            result["already_recorded"].append(row)
            continue
        reason = None
        try:
            date.fromisoformat(row["due_date"])
        except (TypeError, ValueError):
            reason = "INVALID_DUE_DATE"
        if raw.get("currency") != "INR" or type(row["amount_minor"]) is not int or row["amount_minor"] <= 0:
            reason = "INVALID_FINANCIAL_FIELDS"
        elif raw.get("status") != "UNPAID_RECORD":
            reason = raw.get("status") or "UNKNOWN_STATUS"
        elif row["amount_minor"] > limit:
            reason = "EXCEEDS_SAVED_SINGLE_PAYMENT_LIMIT"
        if reason:
            result["review"].append({**row, "reason": reason})
        else:
            candidates.append(row)
    candidates.sort(key=lambda b: (b["due_date"], b["provider_id"], b["bill_reference"]))
    if len(candidates) > max_bills:
        result["state"] = "PLANNING_LIMIT"
        return result
    dates = sorted({b["due_date"] for b in candidates})
    base = len(candidates) + 1
    weights = {d: base ** (len(dates) - i - 1) for i, d in enumerate(dates)}
    # spend -> (lexicographic deadline score, selected indices)
    frontier = {0: (0, ())}
    explored = 1
    for index, bill in enumerate(candidates):
        expanded = dict(frontier)
        for spend, (score, chosen) in frontier.items():
            cost = spend + bill["amount_minor"]
            if cost <= available:
                candidate = (score + weights[bill["due_date"]], chosen + (index,))
                if cost not in expanded or candidate[0] > expanded[cost][0]:
                    expanded[cost] = candidate
        frontier, best = {}, -1
        for cost in sorted(expanded):
            if expanded[cost][0] > best:
                frontier[cost] = expanded[cost]
                best = expanded[cost][0]
        explored += len(frontier)
        if len(frontier) > max_states:
            result["state"] = "PLANNING_LIMIT"
            return result
    cost, (_, chosen) = max(frontier.items(), key=lambda item: (item[1][0], -item[0]))
    result["selected"] = [b for i, b in enumerate(candidates) if i in chosen]
    result["deferred"] = [{**b, "reason": "RESERVE_CONSTRAINED_PRIORITY"} for i, b in enumerate(candidates) if i not in chosen]
    result.update(planned_total_minor=cost, remaining_above_reserve_minor=available-cost,
                  frontier_states_explored=explored)
    return result
