type VideoWithPlayButtonProps = {
  title: string;
  description: string;
  videoUrl?: string;
  thumbnailUrl?: string;
  aspectRatio?: "16/9" | "4/3";
  fallbackText?: string;
  containerId?: string;
};

function extractYouTubeId(url: string): string | null {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();
    if (hostname.includes("youtube.com")) {
      const id = parsed.searchParams.get("v");
      return id && id.trim() ? id.trim() : null;
    }
    if (hostname.includes("youtu.be")) {
      const id = parsed.pathname.split("/").filter(Boolean)[0];
      return id && id.trim() ? id.trim() : null;
    }
  } catch {
    return null;
  }
  return null;
}

function isDirectVideoFile(url: string): boolean {
  try {
    const parsed = new URL(url);
    return /\.(mp4|webm|ogg|mov)$/i.test(parsed.pathname);
  } catch {
    return /\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(url);
  }
}

export default function VideoWithPlayButton({
  title,
  description,
  videoUrl,
  thumbnailUrl,
  aspectRatio = "16/9",
  fallbackText = "Demo video coming soon",
  containerId,
}: VideoWithPlayButtonProps) {
  const hasVideo = Boolean(videoUrl);
  const aspectPaddingBottom = aspectRatio === "16/9" ? "56.25%" : "75%";
  const youtubeId = videoUrl ? extractYouTubeId(videoUrl) : null;
  const directVideo = videoUrl ? isDirectVideoFile(videoUrl) : false;
  const embedUrl = youtubeId
    ? `https://www.youtube-nocookie.com/embed/${youtubeId}?autoplay=1&mute=1&loop=1&playlist=${youtubeId}&controls=1&rel=0&playsinline=1&enablejsapi=1`
    : null;

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
      id={containerId}
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
        }}
      >
        {embedUrl ? (
          <iframe
            src={embedUrl}
            title={title}
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              border: 0,
            }}
          />
        ) : directVideo ? (
          <video
            src={videoUrl}
            poster={thumbnailUrl}
            autoPlay
            loop
            muted
            playsInline
            controls
            preload="metadata"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        ) : (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              background: "linear-gradient(135deg, var(--surface-2) 0%, var(--surface) 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "1rem",
            }}
          >
            <a
              href={videoUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "var(--silver)",
                textDecoration: "underline",
              }}
            >
              Open demo video
            </a>
          </div>
        )}
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
