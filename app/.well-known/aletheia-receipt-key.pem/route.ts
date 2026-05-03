import { NextResponse } from "next/server";
import { getReceiptPublicKey, PublicKeyError } from "@/lib/public-keys";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { pem } = await getReceiptPublicKey();
    return new NextResponse(pem, {
      status: 200,
      headers: {
        "Content-Type": "application/x-pem-file",
        "Cache-Control": "public, max-age=3600",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
      },
    });
  } catch (error) {
    if (error instanceof PublicKeyError) {
      return NextResponse.json(
        { error: error.code, message: error.message },
        { status: error.status },
      );
    }
    return NextResponse.json(
      { error: "public_key_unavailable", message: "Unexpected public key error." },
      { status: 503 },
    );
  }
}
