import type { Metadata } from "next";
import { requireAuth } from "@/lib/server-auth";
import DashboardSidebar from "./DashboardSidebar";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Aletheia Core operational dashboard. Audit logs, policy management, evidence export, and API key administration.",
};

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await requireAuth();
  const user = session.user;

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 60px)" }}>
      {/* Sidebar */}
      <DashboardSidebar userName={user.name} userPlan={user.plan} />
      {/* Main content */}
      <div
        style={{
          flex: 1,
          background: "#09090b",
          padding: "2rem 2.5rem",
          overflowX: "auto",
        }}
      >
        {children}
      </div>
    </div>
  );
}
