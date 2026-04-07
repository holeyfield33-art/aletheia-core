/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep docs/ as a separate static directory — not served by Next.js
  // The app.aletheia-core.com subdomain serves this Next.js app.
  // aletheia-core.com is served separately from docs/index.html.
};

module.exports = nextConfig;
