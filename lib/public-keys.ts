import { createHash, createPrivateKey, createPublicKey, KeyObject } from "node:crypto";
import { readFile } from "node:fs/promises";

type PublicKeyBundle = {
  receiptPem: string;
  receiptKeyId: string;
  manifestPem: string;
  manifestKeyId: string;
};

type ResolvedPublicKey = {
  pem: string;
  keyId: string;
};

const MANIFEST_PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAGI282bHDtzH3fF2s8YjFM1px7zxiLKy1NRZirthzrH8=
-----END PUBLIC KEY-----`;

class PublicKeyError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function readOptionalFile(filePath: string): Promise<string> {
  return readFile(filePath, "utf-8");
}

function keyIdForPublicKey(publicKey: KeyObject): string {
  const der = publicKey.export({ format: "der", type: "spki" });
  return createHash("sha256").update(der).digest("hex").slice(0, 16);
}

async function loadReceiptPublicKeyPem(): Promise<string> {
  const inlinePublicKey = process.env.ALETHEIA_RECEIPT_PUBLIC_KEY?.trim();
  if (inlinePublicKey) {
    createPublicKey(inlinePublicKey);
    return inlinePublicKey;
  }

  const publicKeyPath = process.env.ALETHEIA_RECEIPT_PUBLIC_KEY_PATH?.trim();
  if (publicKeyPath) {
    const pem = (await readOptionalFile(publicKeyPath)).trim();
    createPublicKey(pem);
    return pem;
  }

  const inlinePrivateKey = process.env.ALETHEIA_RECEIPT_PRIVATE_KEY?.trim();
  if (inlinePrivateKey) {
    const publicKey = createPublicKey(createPrivateKey(inlinePrivateKey));
    return publicKey.export({ format: "pem", type: "spki" }).toString();
  }

  const privateKeyPath = process.env.ALETHEIA_RECEIPT_PRIVATE_KEY_PATH?.trim();
  if (privateKeyPath) {
    const privatePem = (await readOptionalFile(privateKeyPath)).trim();
    const publicKey = createPublicKey(createPrivateKey(privatePem));
    return publicKey.export({ format: "pem", type: "spki" }).toString();
  }

  throw new PublicKeyError(
    503,
    "public_key_unavailable",
    "Receipt public key is not configured.",
  );
}

export async function getReceiptPublicKey(): Promise<ResolvedPublicKey> {
  try {
    const pem = await loadReceiptPublicKeyPem();
    return {
      pem,
      keyId: keyIdForPublicKey(createPublicKey(pem)),
    };
  } catch (error) {
    if (error instanceof PublicKeyError) {
      throw error;
    }
    throw new PublicKeyError(
      503,
      "public_key_unavailable",
      `Receipt public key resolution failed: ${String(error)}`,
    );
  }
}

export function getManifestPublicKey(): ResolvedPublicKey {
  try {
    const publicKey = createPublicKey(MANIFEST_PUBLIC_KEY_PEM);
    return {
      pem: MANIFEST_PUBLIC_KEY_PEM,
      keyId: keyIdForPublicKey(publicKey),
    };
  } catch (error) {
    throw new PublicKeyError(
      503,
      "public_key_unavailable",
      `Manifest public key is malformed: ${String(error)}`,
    );
  }
}

export async function getPublicKeyBundle(): Promise<PublicKeyBundle> {
  try {
    const receipt = await getReceiptPublicKey();
    const manifest = getManifestPublicKey();

    return {
      receiptPem: receipt.pem,
      receiptKeyId: receipt.keyId,
      manifestPem: manifest.pem,
      manifestKeyId: manifest.keyId,
    };
  } catch (error) {
    if (error instanceof PublicKeyError) {
      throw error;
    }
    throw new PublicKeyError(
      503,
      "public_key_unavailable",
      `Public key resolution failed: ${String(error)}`,
    );
  }
}

export { PublicKeyError };
