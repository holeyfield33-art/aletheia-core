import { describe, expect, it } from "vitest";

// eslint-disable-next-line @typescript-eslint/no-require-imports
const nextConfig = require("../next.config.js");

describe("policy route tracing config", () => {
  it("includes manifest artifacts for /api/policy", () => {
    expect(nextConfig.outputFileTracingIncludes).toBeDefined();
    expect(nextConfig.outputFileTracingIncludes["/api/policy"]).toEqual(
      expect.arrayContaining([
        "./manifest/security_policy.json",
        "./manifest/security_policy.json.sig",
        "./manifest/security_policy.ed25519.pub",
      ]),
    );
  });
});
