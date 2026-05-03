"""Generate a fresh Ed25519 keypair for receipt signing.

Usage:
    python scripts/generate_receipt_keypair.py [--out-dir .secrets]

Writes:
    <out-dir>/receipt_private.pem  (mode 0600)
    <out-dir>/receipt_public.pem   (mode 0644)
    <out-dir>/key_id.txt           (16 hex chars)

NEVER commit the private key. .gitignore the output directory.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=".secrets", help="Output directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing keys")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    priv_path = out / "receipt_private.pem"
    pub_path = out / "receipt_public.pem"

    if (priv_path.exists() or pub_path.exists()) and not args.force:
        print(f"Refusing to overwrite existing keys in {out}/. Use --force.")
        return 1

    sk = Ed25519PrivateKey.generate()
    priv_pem = sk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = sk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_pem)
    os.chmod(priv_path, 0o600)
    pub_path.write_bytes(pub_pem)
    os.chmod(pub_path, 0o644)

    # Compute key_id matching core/receipt_keys.py:key_id()
    der = sk.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = hashlib.sha256(der).hexdigest()[:16]
    (out / "key_id.txt").write_text(kid + "\n")

    print(f"Generated Ed25519 receipt keypair in {out}/")
    print(f"  Private: {priv_path} (mode 0600)")
    print(f"  Public:  {pub_path}")
    print(f"  Key ID:  {kid}")
    print()
    print("Next steps:")
    print("  1. Add to Vercel env (production):")
    print(f"     ALETHEIA_RECEIPT_PRIVATE_KEY = $(cat {priv_path})")
    print(f"     ALETHEIA_RECEIPT_PUBLIC_KEY  = $(cat {pub_path})")
    print("  2. Verify deployment serves the public key at /.well-known/")
    print("     curl https://aletheia-core.com/.well-known/aletheia-receipt-key.pem")
    print()
    print("DO NOT commit the private key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
