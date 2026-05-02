import type { Metadata } from "next";
import HeroRuntimeFirewall from "@/app/components/landing/HeroRuntimeFirewall";
import RedTeamDemoSection from "@/app/components/landing/RedTeamDemoSection";
import TraderAgentDemoSection from "@/app/components/landing/TraderAgentDemoSection";
import LiveAletheiaDemoSection from "@/app/components/landing/LiveAletheiaDemoSection";
import ReceiptVerificationFlipCard from "@/app/components/landing/ReceiptVerificationFlipCard";
import LandingPricingSection from "@/app/components/landing/LandingPricingSection";
import FinalCTA from "@/app/components/landing/FinalCTA";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Agent Runtime Firewall",
  description:
    "Watch the attack. Watch the agent. Watch Aletheia block the action before execution.",
  alternates: { canonical: URLS.appBase },
};

export default function HomePage() {
  return (
    <>
      <HeroRuntimeFirewall />
      <RedTeamDemoSection videoUrl={process.env.NEXT_PUBLIC_RED_TEAM_DEMO_VIDEO_URL} />
      <TraderAgentDemoSection videoUrl={process.env.NEXT_PUBLIC_TRADER_DEMO_VIDEO_URL} />
      <LiveAletheiaDemoSection />
      <ReceiptVerificationFlipCard />
      <LandingPricingSection />
      <FinalCTA />
      <section style={{ padding: "0 1.5rem 4rem", textAlign: "center" }}>
        <div
          style={{
            color: "var(--muted)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.76rem",
          }}
        >
          {PRODUCT.name} &middot; Protect your agent before it acts.
        </div>
      </section>
    </>
  );
}
