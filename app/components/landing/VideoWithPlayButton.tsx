type VideoWithPlayButtonProps = {
  title: string;
  description: string;
  videoUrl?: string;
  thumbnailUrl?: string;
  aspectRatio?: "16/9" | "4/3";
  fallbackText?: string;
};

export default function VideoWithPlayButton({
  title,
  description,
  videoUrl,
  thumbnailUrl,
  aspectRatio = "16/9",
  fallbackText = "Demo video coming soon",
}: VideoWithPlayButtonProps) {
  const hasVideo = Boolean(videoUrl);
  const aspectPaddingBottom = aspectRatio === "16/9" ? "56.25%" : "75%";

  if (!hasVideo) {
    return (
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          padding: "1.4rem",
          display: "grid",
          gap: "0.8rem",
        }}
      >
        <div
          style={{
            background: "var(--surface-2)",
            borderRadius: "10px",
            padding: "2rem",
            textAlign: "center",
            minHeight: "280px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--muted)", marginBottom: "0.5rem", letterSpacing: "0.1em" }}>VIDEO</div>
            <p style={{ color: "var(--muted)" }}>{fallbackText}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "14px",
        padding: "1.4rem",
        display: "grid",
        gap: "0.8rem",
      }}
    >
      <div
        style={{
          position: "relative",
          width: "100%",
          paddingBottom: aspectPaddingBottom,
          background: "#000",
          borderRadius: "12px",
          overflow: "hidden",
          cursor: "pointer",
          transition: "transform 0.2s ease",
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget.querySelector("img");
          if (el) el.style.transform = "scale(1.02)";
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget.querySelector("img");
          if (el) el.style.transform = "scale(1)";
        }}
      >
        <a href={videoUrl} target="_blank" rel="noopener noreferrer">
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              background: thumbnailUrl
                ? `url(${thumbnailUrl}) center/cover no-repeat`
                : "linear-gradient(135deg, var(--surface-2) 0%, var(--surface) 100%)",
              transition: "transform 0.2s ease",
            }}
          >
            {/* Play button overlay */}
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                width: "80px",
                height: "80px",
                background: "rgba(176, 34, 54, 0.9)",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "3px solid rgba(255, 255, 255, 0.8)",
                transition: "all 0.2s ease",
              }}
            >
              <div
                style={{
                  width: 0,
                  height: 0,
                  borderLeft: "25px solid rgba(255, 255, 255, 0.95)",
                  borderTop: "16px solid transparent",
                  borderBottom: "16px solid transparent",
                  marginLeft: "4px",
                }}
              />
            </div>
          </div>
        </a>
      </div>

      <div>
        <h3 style={{ fontFamily: "var(--font-head)", fontSize: "1.1rem", color: "var(--white)", marginBottom: "0.3rem" }}>
          {title}
        </h3>
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.6 }}>
          {description}
        </p>
      </div>
    </div>
  );
}
