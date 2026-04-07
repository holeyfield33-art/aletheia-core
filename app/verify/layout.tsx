import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Receipt Viewer",
  description:
    "Inspect an Aletheia audit receipt. Paste receipt JSON to view decision, policy hash, payload fingerprint, and signature fields.",
};

export default function VerifyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
