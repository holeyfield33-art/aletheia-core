"""Tests for the cryptographic anchor (TPM interface + chain signer)."""

from __future__ import annotations

import os
import tempfile
import unittest

from crypto.tpm_interface import TPMAnchor
from crypto.chain_signer import ChainSigner, ChainSignatureError


class TestTPMAnchor(unittest.TestCase):
    """TPMAnchor with software fallback (no TPM hardware in CI)."""

    def setUp(self) -> None:
        self.anchor = TPMAnchor()

    def test_backend_type_is_software(self) -> None:
        self.assertEqual(self.anchor.backend_type, "software")

    def test_sign_chain_returns_bytes(self) -> None:
        sig = self.anchor.sign_chain(b"request", b"response", b"nonce")
        self.assertIsInstance(sig, bytes)
        self.assertGreater(len(sig), 0)

    def test_different_inputs_produce_different_signatures(self) -> None:
        sig1 = self.anchor.sign_chain(b"req1", b"res1", b"nonce1")
        sig2 = self.anchor.sign_chain(b"req2", b"res2", b"nonce2")
        self.assertNotEqual(sig1, sig2)

    def test_same_inputs_produce_same_signature(self) -> None:
        sig1 = self.anchor.sign_chain(b"req", b"res", b"nonce")
        sig2 = self.anchor.sign_chain(b"req", b"res", b"nonce")
        self.assertEqual(sig1, sig2)

    def test_public_key_bytes_nonzero(self) -> None:
        pub = self.anchor.public_key_bytes()
        self.assertEqual(len(pub), 32)  # Ed25519 public key is 32 bytes

    def test_key_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "chain.pem")
            os.environ["ALETHEIA_CHAIN_KEY_PATH"] = key_path
            try:
                anchor1 = TPMAnchor()
                pub1 = anchor1.public_key_bytes()
                self.assertTrue(os.path.isfile(key_path))

                # Load again from same file
                anchor2 = TPMAnchor()
                pub2 = anchor2.public_key_bytes()

                self.assertEqual(
                    pub1, pub2, "Persisted key should produce same public key"
                )
            finally:
                os.environ.pop("ALETHEIA_CHAIN_KEY_PATH", None)


class TestChainSigner(unittest.TestCase):
    """Chain signer tests."""

    def setUp(self) -> None:
        self.anchor = TPMAnchor()
        self.signer = ChainSigner(self.anchor)

    def test_verify_and_sign_basic(self) -> None:
        request = {"action": "Read_Report", "payload": "test"}
        response = {"decision": "PROCEED"}
        result = self.signer.verify_and_sign(request, response)
        self.assertIn("_chain_signature", result)
        self.assertIn("_chain_nonce", result)
        self.assertIn("_chain_signer", result)
        self.assertEqual(result["_chain_signer"], "software")

    def test_confused_deputy_detection(self) -> None:
        request = {
            "tool": "calculator",
            "intent": {"specified_tool": "file_reader"},
            "payload": "test",
        }
        response = {"decision": "PROCEED"}
        with self.assertRaises(ChainSignatureError) as ctx:
            self.signer.verify_and_sign(request, response)
        self.assertIn("ASI-04", str(ctx.exception))
        self.assertIn("Confused deputy", str(ctx.exception))

    def test_matching_tool_intent_succeeds(self) -> None:
        request = {
            "tool": "calculator",
            "intent": {"specified_tool": "calculator"},
            "payload": "2+2",
        }
        response = {"result": "4"}
        result = self.signer.verify_and_sign(request, response)
        self.assertIn("_chain_signature", result)

    def test_no_intent_field_succeeds(self) -> None:
        """Requests without intent specification should pass."""
        request = {"action": "Read_Report", "payload": "test"}
        response = {"decision": "PROCEED"}
        result = self.signer.verify_and_sign(request, response)
        self.assertIn("_chain_signature", result)

    def test_signature_verification(self) -> None:
        request = {"action": "Transfer_Funds", "payload": "wire 100"}
        response = {"decision": "DENIED"}
        signed = self.signer.verify_and_sign(request, response)
        # Verify signature is valid
        self.assertTrue(self.signer.verify_signature(request, signed))

    def test_tampered_response_fails_verification(self) -> None:
        request = {"action": "Read_Report", "payload": "test"}
        response = {"decision": "PROCEED"}
        signed = self.signer.verify_and_sign(request, response)
        # Tamper
        signed["decision"] = "DENIED"
        self.assertFalse(self.signer.verify_signature(request, signed))

    def test_missing_signature_fails_verification(self) -> None:
        request = {"action": "Read_Report"}
        response = {"decision": "PROCEED"}
        self.assertFalse(self.signer.verify_signature(request, response))

    def test_unique_nonces(self) -> None:
        request = {"action": "Read_Report", "payload": "test"}
        r1 = self.signer.verify_and_sign(request, {"decision": "PROCEED"})
        r2 = self.signer.verify_and_sign(request, {"decision": "PROCEED"})
        self.assertNotEqual(r1["_chain_nonce"], r2["_chain_nonce"])


if __name__ == "__main__":
    unittest.main()
