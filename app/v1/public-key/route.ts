import { secureJson } from "@/lib/api-utils";
import { getPublicKeyBundle, PublicKeyError } from "@/lib/public-keys";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const bundle = await getPublicKeyBundle();
    return secureJson(
      {
        receipt_key: {
          algorithm: "ed25519",
          key_id: bundle.receiptKeyId,
          pem: bundle.receiptPem,
        },
        manifest_key: {
          algorithm: "ed25519",
          key_id: bundle.manifestKeyId,
          pem: bundle.manifestPem,
        },
      },
      {
        headers: {
          "Cache-Control": "public, max-age=3600",
        },
      },
    );
  } catch (error) {
    if (error instanceof PublicKeyError) {
      return secureJson(
        { error: error.code, message: error.message },
        { status: error.status },
      );
    }
    return secureJson(
      {
        error: "public_key_unavailable",
        message: "Unexpected public key error.",
      },
      { status: 503 },
    );
  }
}
