"""Command-line entry point for the deterministic CARAPACE verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .verifier import verify_payment


def _load_json(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="carapace")
    subcommands = parser.add_subparsers(dest="command", required=True)
    verify = subcommands.add_parser("verify", help="verify payment execution evidence")
    verify.add_argument("contract", help="path to a Payment Assurance Contract JSON file")
    verify.add_argument("evidence", help="path to execution evidence JSON file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        report = verify_payment(_load_json(args.contract), _load_json(args.evidence))
        print(json.dumps(report.as_dict(), indent=2))
        return 0 if report.passed else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

