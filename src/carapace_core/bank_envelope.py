"""Local bank-gateway signatures for immutable pre-payment instructions.

The development key is generated once and pinned on disk. Production must
provide a bank-managed key path; managed KMS and independent identity are later
deployment work, not a property of this local adapter.
"""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_json, sha256_hex


class BankEnvelopeSigner:
    def __init__(self, key_path: Path, *, allow_generate: bool) -> None:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            encoded = key_path.read_bytes()
        except FileNotFoundError:
            if not allow_generate:
                raise RuntimeError("bank signing key must be provisioned outside development")
            new_key = Ed25519PrivateKey.generate()
            encoded = new_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                encoded = key_path.read_bytes()
            else:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(encoded)
        loaded = serialization.load_pem_private_key(encoded, password=None)
        if not isinstance(loaded, Ed25519PrivateKey):
            raise RuntimeError("bank signing key is not Ed25519")
        self._private = loaded
        self.public_key_bytes = loaded.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.key_id = sha256_hex(base64.b64encode(self.public_key_bytes).decode())[:16]

    def sign(self, envelope: Mapping[str, Any]) -> str:
        data = canonical_json(envelope).encode("utf-8")
        return base64.urlsafe_b64encode(self._private.sign(data)).decode("ascii")

    def verify(self, envelope: Mapping[str, Any], signature: str) -> bool:
        return self.verify_with_public_key(envelope, signature, self.public_key_bytes)

    @staticmethod
    def verify_with_public_key(
        envelope: Mapping[str, Any], signature: str, public_key_bytes: bytes
    ) -> bool:
        try:
            raw = base64.urlsafe_b64decode(signature.encode("ascii"))
            Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
                raw, canonical_json(envelope).encode("utf-8")
            )
        except (InvalidSignature, ValueError, TypeError, UnicodeError, binascii.Error):
            return False
        return True
