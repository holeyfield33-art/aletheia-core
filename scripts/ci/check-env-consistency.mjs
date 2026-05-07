#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const CANONICAL_DOC = path.join(ROOT, "docs", "ENVIRONMENT_VARIABLES.md");
const ENV_EXAMPLE = path.join(ROOT, ".env.example");

const CODE_EXTENSIONS = new Set([".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".prisma"]);
const SKIP_DIRS = new Set([
  ".git",
  "node_modules",
  ".next",
  ".venv",
  "venv",
  "dist",
  "build",
  "coverage",
  "out",
]);

const CHECK_MODE = process.argv.find((a) => a.startsWith("--check="))?.split("=")[1] || "all";
const VALID_MODES = new Set(["all", "inventory", "docs", "env-example"]);
if (!VALID_MODES.has(CHECK_MODE)) {
  console.error(`Invalid --check mode '${CHECK_MODE}'. Use one of: ${[...VALID_MODES].join(", ")}`);
  process.exit(2);
}

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(ROOT, full).replaceAll("\\", "/");
    if (rel.startsWith("scripts/ci/")) continue;
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      out.push(...walk(full));
      continue;
    }
    const ext = path.extname(entry.name);
    if (CODE_EXTENSIONS.has(ext)) out.push(full);
  }
  return out;
}

function walkMarkdown(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      out.push(...walkMarkdown(full));
      continue;
    }
    if (entry.name.endsWith(".md")) out.push(full);
  }
  return out;
}

function collectCodeEnvVars() {
  const files = walk(ROOT);
  const vars = new Set();
  const locations = new Map();

  const patterns = [
    /process\.env\.([A-Z][A-Z0-9_]+)/g,
    /process\.env\[\s*["']([A-Z][A-Z0-9_]+)["']\s*\]/g,
    /import\.meta\.env\.([A-Z][A-Z0-9_]+)/g,
    /import\.meta\.env\[\s*["']([A-Z][A-Z0-9_]+)["']\s*\]/g,
    /os\.getenv\(\s*["']([A-Z][A-Z0-9_]+)["']/g,
    /os\.environ\.get\(\s*["']([A-Z][A-Z0-9_]+)["']/g,
    /os\.environ\[\s*["']([A-Z][A-Z0-9_]+)["']\s*\]/g,
    /env_bool\(\s*["']([A-Z][A-Z0-9_]+)["']/g,
    /env\(\s*["']([A-Z][A-Z0-9_]+)["']\s*\)/g, // Prisma schema env("...")
  ];

  for (const file of files) {
    const text = fs.readFileSync(file, "utf8");
    for (const re of patterns) {
      let m;
      while ((m = re.exec(text)) !== null) {
        const v = m[1];
        vars.add(v);
        if (!locations.has(v)) locations.set(v, new Set());
        locations.get(v).add(path.relative(ROOT, file));
      }
      re.lastIndex = 0;
    }
  }
  return { vars, locations };
}

function collectDynamicConfigEnvVars() {
  const cfgPath = path.join(ROOT, "core", "config.py");
  const out = new Set();
  if (!fs.existsSync(cfgPath)) return out;
  const text = fs.readFileSync(cfgPath, "utf8");

  const classStart = text.indexOf("class AletheiaSettings:");
  const postInit = text.indexOf("def __post_init__", classStart);
  if (classStart < 0 || postInit < 0) return out;
  const classSlice = text.slice(classStart, postInit);

  // Dataclass fields in AletheiaSettings map to ALETHEIA_<UPPER_FIELD_NAME>.
  const fieldRe = /^\s{4}([a-z_][a-z0-9_]*)\s*:\s*[^=]+=/gm;
  let m;
  while ((m = fieldRe.exec(classSlice)) !== null) {
    const name = m[1];
    if (name === "shadow_mode") continue;
    out.add(`ALETHEIA_${name.toUpperCase()}`);
  }

  // Dynamic quota env names are built via f-strings in key_store.py.
  out.add("ALETHEIA_TRIAL_QUOTA");
  out.add("ALETHEIA_PRO_QUOTA");
  out.add("ALETHEIA_MAX_QUOTA");

  return out;
}

function parseCanonicalDoc() {
  if (!fs.existsSync(CANONICAL_DOC)) {
    throw new Error(`Missing canonical doc: ${path.relative(ROOT, CANONICAL_DOC)}`);
  }
  const text = fs.readFileSync(CANONICAL_DOC, "utf8");

  const all = new Set();
  const required = new Set();

  // Table rows: | VAR | Status | ...
  const tableRow = /^\|\s*([A-Z][A-Z0-9_]+)\s*\|\s*([^|]+)\|/gm;
  let row;
  while ((row = tableRow.exec(text)) !== null) {
    const v = row[1].trim();
    const status = row[2].trim().toLowerCase();
    all.add(v);
    if (status.includes("required") || status === "yes") required.add(v);
  }

  // Non-runtime bullet list in canonical doc.
  const bullet = /^-\s+([A-Z][A-Z0-9_]+)\s*$/gm;
  let b;
  while ((b = bullet.exec(text)) !== null) {
    all.add(b[1]);
  }

  return { all, required };
}

function parseEnvExample() {
  if (!fs.existsSync(ENV_EXAMPLE)) {
    throw new Error(`Missing env template: ${path.relative(ROOT, ENV_EXAMPLE)}`);
  }
  const text = fs.readFileSync(ENV_EXAMPLE, "utf8");
  const names = new Set();
  const comments = new Map();

  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(/^\s*#?\s*([A-Z][A-Z0-9_]+)\s*=/);
    if (!m) continue;
    const v = m[1];
    names.add(v);

    // Capture immediately preceding comment block.
    const commentLines = [];
    for (let j = i - 1; j >= 0; j--) {
      const prev = lines[j].trim();
      if (!prev) {
        if (commentLines.length > 0) break;
        continue;
      }
      if (!prev.startsWith("#")) break;
      commentLines.push(prev);
    }
    comments.set(v, commentLines.reverse().join("\n"));
  }

  return { names, comments };
}

function parseMarkdownRequiredLists() {
  const markdownFiles = walkMarkdown(ROOT);

  const result = new Map();

  for (const file of markdownFiles) {
    const rel = path.relative(ROOT, file);
    if (rel === "docs/ENVIRONMENT_VARIABLES.md") continue;

    const text = fs.readFileSync(file, "utf8");

    // Enforce for README and docs marked for strict required-var sync.
    const enforce =
      rel === "README.md" ||
      text.includes("<!-- ENV_REQUIRED_SYNC -->");
    if (!enforce) continue;

    const found = new Set();

    // Table rows where first column is env var and second includes required-ish text.
    const tableRow = /^\|\s*`?([A-Z][A-Z0-9_]+)`?\s*\|\s*([^|]+)\|/gm;
    let m;
    while ((m = tableRow.exec(text)) !== null) {
      const v = m[1].trim();
      const status = m[2].toLowerCase();
      if (status.includes("required") || status.trim() === "yes") found.add(v);
    }

    result.set(rel, found);
  }

  return result;
}

function sorted(set) {
  return [...set].sort();
}

function setDiff(a, b) {
  const out = [];
  for (const x of a) if (!b.has(x)) out.push(x);
  return out.sort();
}

function printSection(title, lines) {
  if (lines.length === 0) return;
  console.error(`\n${title}`);
  for (const line of lines) console.error(`  - ${line}`);
}

function main() {
  const { vars: codeVars, locations } = collectCodeEnvVars();
  const dynamicVars = collectDynamicConfigEnvVars();
  for (const v of dynamicVars) codeVars.add(v);
  const canonical = parseCanonicalDoc();
  const envExample = parseEnvExample();

  let failed = false;

  // 1) Inventory parity: code vs canonical doc list.
  const missingInDoc = setDiff(codeVars, canonical.all);
  const staleInDoc = setDiff(canonical.all, codeVars);

  if ((CHECK_MODE === "all" || CHECK_MODE === "inventory") && (missingInDoc.length || staleInDoc.length)) {
    failed = true;
    console.error("ERROR: Environment variable inventory drift detected.");

    if (missingInDoc.length) {
      printSection("Used in code but missing from docs/ENVIRONMENT_VARIABLES.md:", missingInDoc);
      for (const v of missingInDoc) {
        const files = sorted(locations.get(v) || new Set());
        console.error(`    ${v} used in: ${files.join(", ")}`);
      }
    }

    if (staleInDoc.length) {
      printSection("Documented but not found in code:", staleInDoc);
    }
  }

  // 2) .env.example must include all required vars from canonical list.
  const missingRequiredInEnvExample = setDiff(canonical.required, envExample.names);
  if ((CHECK_MODE === "all" || CHECK_MODE === "env-example") && missingRequiredInEnvExample.length) {
    failed = true;
    console.error("\nERROR: .env.example is missing required variables.");
    printSection("Missing required entries:", missingRequiredInEnvExample);
  }

  // 3) Optional quality gate: required vars should have comments in .env.example.
  // Enabled only when STRICT_ENV_EXAMPLE_COMMENTS=true.
  const strictComments =
    (process.env.STRICT_ENV_EXAMPLE_COMMENTS || "").toLowerCase() === "true";
  const requiredNoComment = sorted(canonical.required).filter((v) => {
    if (!envExample.names.has(v)) return false;
    const c = envExample.comments.get(v) || "";
    return c.trim().length === 0;
  });
  if ((CHECK_MODE === "all" || CHECK_MODE === "env-example") && strictComments && requiredNoComment.length) {
    failed = true;
    console.error("\nERROR: .env.example required variables are missing explanatory comments.");
    printSection("Add a comment above each required variable:", requiredNoComment);
  }

  // 4) README/docs required-list consistency.
  if (CHECK_MODE === "all" || CHECK_MODE === "docs") {
    const requiredLists = parseMarkdownRequiredLists();
    for (const [file, found] of requiredLists.entries()) {
      const missing = setDiff(canonical.required, found);
      const extra = setDiff(found, canonical.required);
      if (missing.length || extra.length) {
        failed = true;
        console.error(`\nERROR: Required env list mismatch in ${file}`);
        printSection("Missing required vars compared to canonical:", missing);
        printSection("Extra vars not marked required in canonical:", extra);
      }
    }
  }

  if (failed) {
    console.error("\nFix guidance:");
    console.error("  1) Update docs/ENVIRONMENT_VARIABLES.md to match actual code usage.");
    console.error("  2) Ensure .env.example contains all required vars with comments.");
    console.error("  3) Align any README/docs required-var sections with canonical required list.");
    process.exit(1);
  }

  const inventory = sorted(codeVars);
  console.log(`PASS: env inventory check succeeded (${inventory.length} variables).`);
}

main();
