"""Independent client for pinning and checking CARAPACE witness checkpoints.

The monitor accepts a witness public key from a separate file, never from the
checkpoint API. A local file is a demonstration of retained state; a real
monitor must run under a separate operator and share checkpoints to detect
split views served to different observers.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

from .bank_envelope import BankEnvelopeSigner
from .canonical import canonical_json, sha256_hex
from .protection_proof import verify_consistency


class CheckpointRejected(ValueError):
    pass


def _signed_head(head: Any, signature: Any, public_key: bytes) -> tuple[int, bytes]:
    if not isinstance(head, dict) or not isinstance(signature, str):
        raise CheckpointRejected("checkpoint head or signature is missing")
    expected_key_id = sha256_hex(base64.b64encode(public_key).decode("ascii"))[:16]
    if head.get("schema_version") != "carapace-tree-head-1":
        raise CheckpointRejected("unknown witness checkpoint schema")
    if head.get("witness_key_id") != expected_key_id:
        raise CheckpointRejected("checkpoint does not use the pinned witness key")
    size = head.get("tree_size")
    if type(size) is not int or size < 1:
        raise CheckpointRejected("invalid checkpoint tree size")
    try:
        root = bytes.fromhex(head["root_hash"])
    except (KeyError, TypeError, ValueError) as error:
        raise CheckpointRejected("invalid checkpoint root") from error
    if len(root) != 32 or not BankEnvelopeSigner.verify_with_public_key(
        head, signature, public_key
    ):
        raise CheckpointRejected("checkpoint signature or root is invalid")
    return size, root


def verify_checkpoint_response(
    response: Mapping[str, Any], *, previous_state: Mapping[str, Any] | None,
    witness_public_key: bytes,
) -> dict[str, Any]:
    """Return a new state only if the signed head extends the retained one."""
    if len(witness_public_key) != 32:
        raise CheckpointRejected("pinned witness key must be 32 bytes")
    if response.get("schema_version") != "carapace-consistency-1":
        raise CheckpointRejected("unknown consistency response schema")
    head, signature = response.get("current_head"), response.get("current_signature")
    size, root = _signed_head(head, signature, witness_public_key)
    nodes = response.get("consistency_path")
    if not isinstance(nodes, list):
        raise CheckpointRejected("consistency path is missing")
    try:
        path = [bytes.fromhex(node) for node in nodes]
    except (TypeError, ValueError) as error:
        raise CheckpointRejected("consistency path contains invalid hex") from error
    if previous_state is None:
        if response.get("previous_head") is not None or response.get("previous_signature") is not None or path:
            raise CheckpointRejected("bootstrap response unexpectedly contains a prior proof")
    else:
        if previous_state.get("schema_version") != "carapace-monitor-state-1":
            raise CheckpointRejected("saved monitor state has an unknown schema")
        retained_head = previous_state.get("head")
        retained_signature = previous_state.get("signature")
        old_size, old_root = _signed_head(
            retained_head, retained_signature, witness_public_key
        )
        if (
            response.get("previous_head") != retained_head
            or response.get("previous_signature") != retained_signature
        ):
            raise CheckpointRejected("server history disagrees with retained checkpoint")
        if size < old_size:
            raise CheckpointRejected("witness checkpoint rolled back")
        if not verify_consistency(old_size, size, old_root, root, path):
            raise CheckpointRejected("witness history is not append-only")
    return {
        "schema_version": "carapace-monitor-state-1",
        "head": head,
        "signature": signature,
    }


def _fetch_checkpoint(base_url: str, from_size: int) -> dict[str, Any]:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CheckpointRejected("URL must be an HTTP(S) origin")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise CheckpointRejected("remote witness monitors require HTTPS")
    url = base_url.rstrip("/") + "/v1/preflight/log/checkpoint?" + urlencode({"from_size": from_size})
    with urlopen(url, timeout=10) as reply:  # nosec: explicit operator URL; HTTPS required remotely
        body = reply.read(1_000_001)
    if len(body) > 1_000_000:
        raise CheckpointRejected("checkpoint response is too large")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise CheckpointRejected("checkpoint response must be an object")
    return value


def _save_state(path: Path, state: Mapping[str, Any]) -> None:
    if not path.parent.is_dir():
        raise CheckpointRejected("state directory does not exist")
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".carapace-monitor-",
            delete=False,
        ) as handle:
            temp_path = handle.name
            os.chmod(temp_path, 0o600)
            handle.write(canonical_json(state) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.unlink(temp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pin and verify CARAPACE witness history")
    parser.add_argument("--url", required=True, help="CARAPACE API origin")
    parser.add_argument("--state-file", required=True, type=Path)
    parser.add_argument("--witness-public-key-file", required=True, type=Path,
                        help="separately pinned base64 raw Ed25519 public key")
    args = parser.parse_args()
    try:
        public_key = base64.b64decode(
            args.witness_public_key_file.read_text(encoding="utf-8").strip(), validate=True
        )
        previous = (
            json.loads(args.state_file.read_text(encoding="utf-8"))
            if args.state_file.exists() else None
        )
        from_size = previous["head"]["tree_size"] if previous is not None else 0
        response = _fetch_checkpoint(args.url, from_size)
        state = verify_checkpoint_response(
            response, previous_state=previous, witness_public_key=public_key,
        )
        _save_state(args.state_file, state)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"checkpoint rejected: {error}\n")
    print(f"Verified append-only witness checkpoint: {state['head']['tree_size']} leaves")


if __name__ == "__main__":
    main()
