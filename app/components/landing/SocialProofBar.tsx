"use client";

import { useEffect, useState } from "react";

export default function SocialProofBar() {
  const [starCount, setStarCount] = useState<number | null>(null);

  useEffect(() => {
    // Fetch GitHub star count from GitHub API
    const fetchStars = async () => {
      try {
        const response = await fetch("https://api.github.com/repos/holeyfield33-art/aletheia-core");
        if (response.ok) {
          const data = await response.json();
          setStarCount(data.stargazers_count);
        }
      } catch (error) {
        console.error("Failed to fetch GitHub stars:", error);
      }
    };

    fetchStars();
  }, []);

  return (
    <section style={{ padding: "1.5rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div
          style={{
            display: "flex",
            gap: "2rem",
            justifyContent: "center",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.8rem",
                color: "var(--crimson-hi)",
                fontWeight: 700,
              }}
            >
              {starCount !== null ? starCount.toLocaleString() : "1K+"}
            </div>
            <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              GitHub Stars
            </div>
          </div>

          <div style={{ width: "1px", height: "40px", background: "var(--border)" }} />

          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.8rem",
                color: "var(--green)",
                fontWeight: 700,
              }}
            >
              100+
            </div>
            <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              Protected Agents
            </div>
          </div>

          <div style={{ width: "1px", height: "40px", background: "var(--border)" }} />

          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.8rem",
                color: "var(--green)",
                fontWeight: 700,
              }}
            >
              1M+
            </div>
            <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              Decisions Secured
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
