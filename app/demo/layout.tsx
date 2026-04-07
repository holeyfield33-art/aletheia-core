import type { Metadata } from "next";
import { DemoErrorBoundary } from "@/app/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "Live Demo",
  description:
    "Send a test payload through a live Aletheia audit engine. See the decision and signed receipt in real time. No install required.",
};

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return <DemoErrorBoundary>{children}</DemoErrorBoundary>;
}
