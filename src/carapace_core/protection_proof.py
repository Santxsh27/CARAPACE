"""Domain-separated SHA-256 Merkle proofs for signed protection records.

The tree shape and proof algorithms follow RFC 9162 Section 2.1. Inclusion
establishes membership in one tree head; consistency proves a later head is
an append-only extension of a previously saved head. Neither proves coverage.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from .bank_envelope import BankEnvelopeSigner
from .canonical import canonical_json


def leaf_hash(record: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(b"\x00" + canonical_json(record).encode("utf-8")).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _split_point(size: int) -> int:
    return 1 << ((size - 1).bit_length() - 1)


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    size = len(leaves)
    if size == 0:
        return hashlib.sha256(b"").digest()
    if size == 1:
        return leaves[0]
    split = _split_point(size)
    return _node_hash(merkle_root(leaves[:split]), merkle_root(leaves[split:]))


def inclusion_path(leaves: Sequence[bytes], index: int) -> list[bytes]:
    size = len(leaves)
    if not 0 <= index < size:
        raise ValueError("leaf index is outside tree")
    if size == 1:
        return []
    split = _split_point(size)
    if index < split:
        return inclusion_path(leaves[:split], index) + [merkle_root(leaves[split:])]
    return inclusion_path(leaves[split:], index - split) + [merkle_root(leaves[:split])]


def consistency_path(leaves: Sequence[bytes], first_size: int) -> list[bytes]:
    """RFC 9162 SUBPROOF for 0 < first_size <= len(leaves)."""
    if not 0 < first_size <= len(leaves):
        raise ValueError("first tree size is outside the current tree")
    if first_size == len(leaves):
        return []

    def subproof(first: int, current: Sequence[bytes], known: bool) -> list[bytes]:
        if first == len(current):
            return [] if known else [merkle_root(current)]
        split = _split_point(len(current))
        if first <= split:
            return subproof(first, current[:split], known) + [merkle_root(current[split:])]
        return subproof(first - split, current[split:], False) + [merkle_root(current[:split])]

    return subproof(first_size, leaves, True)


def verify_consistency(
    first_size: int, second_size: int, first_root: bytes,
    second_root: bytes, path: Sequence[bytes],
) -> bool:
    """Verify RFC 9162 Section 2.1.4.2 without access to the leaves."""
    if (
        type(first_size) is not int or type(second_size) is not int
        or first_size < 1 or first_size > second_size
        or len(first_root) != 32 or len(second_root) != 32
        or any(len(node) != 32 for node in path)
    ):
        return False
    if first_size == second_size:
        return not path and first_root == second_root
    nodes = list(path)
    if first_size & (first_size - 1) == 0:
        nodes.insert(0, first_root)
    if not nodes:
        return False
    first_index, second_index = first_size - 1, second_size - 1
    while first_index & 1:
        first_index >>= 1
        second_index >>= 1
    first_hash = second_hash = nodes[0]
    for node in nodes[1:]:
        if second_index == 0:
            return False
        if first_index & 1 or first_index == second_index:
            first_hash = _node_hash(node, first_hash)
            second_hash = _node_hash(node, second_hash)
            if not first_index & 1:
                while first_index != 0 and not first_index & 1:
                    first_index >>= 1
                    second_index >>= 1
        else:
            second_hash = _node_hash(second_hash, node)
        first_index >>= 1
        second_index >>= 1
    return (
        second_index == 0 and first_hash == first_root and second_hash == second_root
    )


def verify_inclusion(
    leaf: bytes, index: int, size: int, path: Sequence[bytes], expected_root: bytes
) -> bool:
    if size < 1 or not 0 <= index < size or len(leaf) != 32 or len(expected_root) != 32:
        return False
    if any(len(node) != 32 for node in path):
        return False
    nodes = iter(path)

    def rebuild(position: int, count: int) -> bytes:
        if count == 1:
            return leaf
        split = _split_point(count)
        if position < split:
            return _node_hash(rebuild(position, split), next(nodes))
        right = rebuild(position - split, count - split)
        return _node_hash(next(nodes), right)

    try:
        actual = rebuild(index, size)
    except StopIteration:
        return False
    return actual == expected_root and next(nodes, None) is None


def verify_protection_bundle(
    bundle: Mapping[str, Any], *, bank_public_key: bytes, witness_public_key: bytes
) -> bool:
    """Verify using externally pinned keys, never keys supplied by the bundle."""
    try:
        receipt = bundle["receipt"]
        bank_signature = bundle["bank_signature"]
        tree_head = bundle["tree_head"]
        head_signature = bundle["head_signature"]
        path = [bytes.fromhex(value) for value in bundle["inclusion_path"]]
        index = bundle["leaf_index"]
        size = tree_head["tree_size"]
        if type(index) is not int or type(size) is not int:
            return False
        if not BankEnvelopeSigner.verify_with_public_key(
            receipt, bank_signature, bank_public_key
        ):
            return False
        if not BankEnvelopeSigner.verify_with_public_key(
            tree_head, head_signature, witness_public_key
        ):
            return False
        record = {"receipt": receipt, "bank_signature": bank_signature}
        computed_leaf = leaf_hash(record)
        if computed_leaf.hex() != bundle["leaf_hash"]:
            return False
        return verify_inclusion(
            computed_leaf, index, size, path, bytes.fromhex(tree_head["root_hash"])
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
