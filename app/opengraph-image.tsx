import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Aletheia Core — Runtime audit and pre-execution block layer for AI agents";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          background: "#080a0c",
          padding: "60px 80px",
        }}
      >
        {/* Top accent line */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "4px",
            background: "#8B1A2A",
          }}
        />

        {/* Logo / brand mark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "rgba(139, 26, 42, 0.2)",
              border: "2px solid #8B1A2A",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "24px",
              color: "#B02236",
              fontWeight: 800,
            }}
          >
            A
          </div>
          <span
            style={{
              fontSize: "28px",
              fontWeight: 700,
              color: "#f0eee8",
              letterSpacing: "-0.02em",
            }}
          >
            Aletheia Core
          </span>
        </div>

        {/* Main headline */}
        <div
          style={{
            fontSize: "52px",
            fontWeight: 800,
            color: "#f0eee8",
            textAlign: "center",
            lineHeight: 1.15,
            maxWidth: "900px",
            marginBottom: "24px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <span>Runtime audit &amp;</span>
          <span style={{ color: "#B02236" }}>pre-execution block layer</span>
          <span>for AI agents</span>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "20px",
            color: "#8b95a5",
            textAlign: "center",
            maxWidth: "700px",
            lineHeight: 1.5,
          }}
        >
          Cryptographically signed enforcement · Semantic policy hardening · Tamper-evident audit receipts
        </div>

        {/* Bottom badges */}
        <div
          style={{
            position: "absolute",
            bottom: "40px",
            display: "flex",
            gap: "24px",
          }}
        >
          {["MIT Licensed", "957 Tests", "Open Source", "Signed Receipts"].map(
            (badge) => (
              <div
                key={badge}
                style={{
                  fontSize: "14px",
                  color: "#A8B0B8",
                  padding: "6px 16px",
                  border: "1px solid #1e2530",
                  borderRadius: "6px",
                  background: "#0e1115",
                }}
              >
                {badge}
              </div>
            ),
          )}
        </div>
      </div>
    ),
    { ...size },
  );
}
