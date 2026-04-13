import fs from "fs";
import path from "path";

// read CHANGELOG.md at build time
const changelogPath = path.join(process.cwd(), "CHANGELOG.md");
const changelogContent = fs.readFileSync(changelogPath, "utf-8");

// parse section version headers: ## [VERSION] — DATE
const sections = changelogContent
  .split(/^## \[/m)
  .slice(1) // skip header before first section
  .map((section) => {
    const lines = section.split("\n");
    const headerLine = lines[0];
    const [version, ...rest] = headerLine.split("]");
    const date = rest.join("]").replace(/\s*—\s*/, "").trim();

    return {
      version: version.trim(),
      date,
      content: lines.slice(1).join("\n").trim(),
    };
  });

export default function ChangelogPage() {
  return (
    <div style={{ maxWidth: "960px", margin: "0 auto", padding: "3rem 2rem" }}>
      <h1
        style={{
          fontSize: "2.2rem",
          fontFamily: "var(--font-head)",
          fontWeight: 800,
          marginBottom: "0.5rem",
        }}
      >
        Changelog
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.95rem",
          marginBottom: "3rem",
        }}
      >
        All notable changes to Aletheia Core. Format follows{" "}
        <a href="https://keepachangelog.com/en/1.0.0/" target="_blank">
          Keep a Changelog
        </a>
        .
      </p>

      {sections.map((section) => (
        <section key={section.version} style={{ marginBottom: "3rem" }}>
          <h2
            style={{
              fontSize: "1.35rem",
              fontFamily: "var(--font-head)",
              fontWeight: 700,
              marginBottom: "0.25rem",
            }}
          >{`[${section.version}] — ${section.date}`}</h2>
          <div
            style={{
              color: "var(--silver)",
              lineHeight: 1.8,
              marginTop: "1rem",
            }}
            dangerouslySetInnerHTML={{
              __html: markdownToHtml(section.content),
            }}
          />
        </section>
      ))}
    </div>
  );
}

function markdownToHtml(md: string): string {
  return md
    .split("\n")
    .map((line) => {
      // h3: ### Added
      if (line.startsWith("### ")) {
        return `<h3 style="font-size:1.1rem; font-weight:700; margin:1.5rem 0 0.75rem; color:var(--crimson-hi)">${line.slice(4)}</h3>`;
      }
      // ul list: - item
      if (line.startsWith("- ")) {
        return `<li style="margin-left:1.5rem; margin-bottom:0.5rem">${
          line.slice(2)
        }</li>`;
      }
      // hr: ---
      if (line === "---") {
        return `<hr style="border:none; border-top:1px solid var(--border); margin:2rem 0" />`;
      }
      // paragraph
      if (line.trim() && !line.startsWith("- ") && !line.startsWith("### ") && line !== "---") {
        return `<p style="margin-bottom:0.75rem">${line}</p>`;
      }
      return ""; // empty
    })
    .join("\n")
    .replace(/(<li[^>]*>[^<]*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank">$1</a>'
    );
}

export const metadata = {
  title: "Changelog",
  description: "Version history and release notes for Aletheia Core.",
};
