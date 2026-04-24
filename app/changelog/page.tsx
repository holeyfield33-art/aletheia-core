import fs from "fs";
import path from "path";
import type { ReactNode } from "react";

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
          >
            {renderMarkdown(section.content)}
          </div>
        </section>
      ))}
    </div>
  );
}

function renderMarkdown(md: string): ReactNode[] {
  const lines = md.split("\n");
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length === 0) return;
    nodes.push(
      <ul key={`list-${nodes.length}`} style={{ margin: "0 0 1rem 1.5rem" }}>
        {listItems.map((item, index) => (
          <li key={index} style={{ marginBottom: "0.5rem" }}>
            {renderInlineLinks(item)}
          </li>
        ))}
      </ul>
    );
    listItems = [];
  }

  for (const line of lines) {
    if (line.startsWith("- ")) {
      listItems.push(line.slice(2));
      continue;
    }

    flushList();

    if (line.startsWith("### ")) {
      nodes.push(
        <h3
          key={`h3-${nodes.length}`}
          style={{
            fontSize: "1.1rem",
            fontWeight: 700,
            margin: "1.5rem 0 0.75rem",
            color: "var(--crimson-hi)",
          }}
        >
          {line.slice(4)}
        </h3>
      );
      continue;
    }

    if (line === "---") {
      nodes.push(
        <hr
          key={`hr-${nodes.length}`}
          style={{ border: "none", borderTop: "1px solid var(--border)", margin: "2rem 0" }}
        />
      );
      continue;
    }

    if (line.trim()) {
      nodes.push(
        <p key={`p-${nodes.length}`} style={{ marginBottom: "0.75rem" }}>
          {renderInlineLinks(line)}
        </p>
      );
    }
  }

  flushList();
  return nodes;
}

function renderInlineLinks(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
  let lastIndex = 0;

  for (const match of text.matchAll(linkPattern)) {
    const [fullMatch, label, href] = match;
    const start = match.index ?? 0;

    if (start > lastIndex) {
      parts.push(text.slice(lastIndex, start));
    }

    parts.push(
      <a key={`${href}-${start}`} href={href} target="_blank" rel="noreferrer">
        {label}
      </a>
    );

    lastIndex = start + fullMatch.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export const metadata = {
  title: "Changelog",
  description: "Version history and release notes for Aletheia Core.",
};
