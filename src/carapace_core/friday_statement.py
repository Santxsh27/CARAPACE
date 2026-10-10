"""Read-only INR statement analysis. Imported claims never authorize payments."""
from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256


def _money(value: str) -> int:
    value = value.strip().removeprefix("INR").removeprefix("₹").strip()
    if not value:
        return 0
    if "," in value:
        if not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?", value):
            raise ValueError("Invalid amount grouping")
        value = value.replace(",", "")
    if not re.fullmatch(r"\d{1,12}(?:\.\d{1,2})?", value):
        raise ValueError("Amounts must be non-negative INR values with at most two decimals")
    return int(Decimal(value) * 100)


def analyze_statement(text: str) -> dict:
    if not text or len(text.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Use a non-empty CSV of at most 1 MB")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    if len(set(headers)) != len(headers):
        raise ValueError("Duplicate column names are not supported")
    required = {"date", "description", "debit", "credit"}
    if not required.issubset(headers):
        raise ValueError("Required columns: date, description, debit, credit. Values must be INR rupees.")
    entries, months, repeated = [], defaultdict(lambda: {"debit_minor": 0, "credit_minor": 0}), Counter()
    try:
        for index, original in enumerate(reader, 2):
            if len(entries) >= 5000:
                raise ValueError("Maximum 5,000 transactions; export a smaller date range")
            if None in original or any(v is None for v in original.values()):
                raise ValueError(f"Row {index}: inconsistent number of columns")
            row = {k.strip().lower(): v.strip() for k, v in original.items()}
            if row.get("currency", "INR").upper() != "INR":
                raise ValueError(f"Row {index}: only INR statements are supported; currencies cannot be mixed")
            date = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    date = datetime.strptime(row["date"], fmt).date().isoformat()
                    break
                except ValueError:
                    continue
            if date is None:
                raise ValueError(f"Row {index}: use YYYY-MM-DD or DD/MM/YYYY dates")
            description = row["description"]
            if not description or len(description) > 500:
                raise ValueError(f"Row {index}: description must contain 1–500 characters")
            try:
                debit, credit = _money(row["debit"]), _money(row["credit"])
            except ValueError as error:
                raise ValueError(f"Row {index}: {error}") from error
            if bool(debit) == bool(credit):
                raise ValueError(f"Row {index}: exactly one of debit or credit must be positive")
            entry = {"row": index, "date": date, "description": description,
                     "debit_minor": debit, "credit_minor": credit}
            entries.append(entry)
            repeated[(date, description.casefold(), debit, credit)] += 1
            months[date[:7]]["debit_minor"] += debit
            months[date[:7]]["credit_minor"] += credit
    except csv.Error as error:
        raise ValueError("Malformed CSV; no partial result was accepted") from error
    if not entries:
        raise ValueError("No transaction rows found")
    outgoing = sum(e["debit_minor"] for e in entries)
    incoming = sum(e["credit_minor"] for e in entries)
    return {
        "scope": "USER_SUPPLIED_STATEMENT", "currency": "INR", "read_only": True,
        "money_moved": False, "raw_file_stored": False, "sent_to_ai": False,
        "statement_sha256": sha256(text.encode()).hexdigest(), "transaction_count": len(entries),
        "period": {"start": min(e["date"] for e in entries), "end": max(e["date"] for e in entries)},
        "totals": {"money_in_minor": incoming, "money_out_minor": outgoing,
                   "net_flow_minor": incoming - outgoing},
        "monthly": [{"month": month, **values} for month, values in sorted(months.items())],
        "largest_outgoing": sorted((e for e in entries if e["debit_minor"]),
                                   key=lambda e: (-e["debit_minor"], e["row"]))[:10],
        "repeated_rows": [{"date": key[0], "description": key[1], "debit_minor": key[2],
                           "credit_minor": key[3], "count": count}
                          for key, count in repeated.items() if count > 1][:20],
        "limits": ["User-supplied data, not authenticated bank evidence or a complete financial profile.",
                   "All rows are included in totals. Repeated entries may be legitimate; no fraud verdict or automatic deletion.",
                   "Net flow is not your account balance. No sandbox balance, bill status or payment permission was changed.",
                   "Processing is ephemeral on the Friday server; raw statements are not saved or sent to Gemini."],
    }
