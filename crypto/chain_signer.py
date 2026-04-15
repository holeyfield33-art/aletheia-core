"""Gate C1: Chain integrity and intent binding.

Verifies that ``request.tool == request.intent.specified_tool``
(confused-deputy prevention), then computes and signs
SHA3-256(R || S || nonce) using the TPM anchor.
"""
from __future__ import annotations

import logging
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from crypto.tpm_interface import TPMAnchor

_logger = logging.getLogger("aletheia.crypto.chain_signer")


class ChainSignatureError(Exception):
    """Raised when chain signing or verification fails."""


class ChainSigner:
    """Signs the full request→response chain and detects confused deputies."""

    def __init__(self, tpm: TPMAnchor) -> None:
        self._tpm = tpm

    def verify_and_sign(self, request: dict, response: dict) -> dict:
        """Gate C1: verify intent alignment, then sign the chain.

        Raises ``ChainSignatureError`` if the tool does not match the
        declared intent (ASI-04 confused deputy prevention).

        Returns *response* augmented with ``_chain_signature`` and
        ``_chain_nonce``.
        """
        intent = request.get("intent", {})
        specified_tool = intent.get("specified_tool")
        actual_tool = request.get("tool")

        if specified_tool is not None and actual_tool != specified_tool:
            raise ChainSignatureError(
                f"ASI-04: Confused deputy — tool={actual_tool!r} "
                f"does not match intent.specified_tool={specified_tool!r}"
            )

        req_bytes = _canonical(request)
        res_bytes = _canonical(response)
        nonce = os.urandom(32)

        signature = self._tpm.sign_chain(req_bytes, res_bytes, nonce)

        response["_chain_signature"] = signature.hex()
        response["_chain_nonce"] = nonce.hex()
        response["_chain_signer"] = self._tpm.backend_type
        return response

    def verify_signature(self, request: dict, response: dict) -> bool:
        """Verify a previously signed chain response.

        Returns True if the signature is valid.
        """
        sig_hex = response.get("_chain_signature")
        nonce_hex = response.get("_chain_nonce")
        if not sig_hex or not nonce_hex:
            return False

        req_bytes = _canonical(request)
        # Build response without chain metadata for verification
        res_copy = {
            k: v for k, v in response.items()
            if k not in ("_chain_signature", "_chain_nonce", "_chain_signer")
        }
        res_bytes = _canonical(res_copy)

        from cryptography.hazmat.primitives import hashes

        h = hashes.Hash(hashes.SHA3_256())
        h.update(req_bytes)
        h.update(res_bytes)
        h.update(bytes.fromhex(nonce_hex))
        digest = h.finalize()

        pub_bytes = self._tpm.public_key_bytes()
        pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        try:
            pub_key.verify(bytes.fromhex(sig_hex), digest)
            return True
        except Exception:
            return False


def _canonical(obj: dict) -> bytes:
    """Deterministic serialisation for signing.

    Sorts keys to ensure reproducible digests regardless of
    insertion order.
    """
    import json
    return json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
