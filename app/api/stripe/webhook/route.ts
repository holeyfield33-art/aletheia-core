// Intentional alias: /api/stripe/webhook re-exports the canonical handler at
// /api/webhooks/stripe. Documented in docs/API_REFERENCE.md; existing Stripe
// webhook endpoints in production reference this URL. Do not delete without
// updating the Stripe Dashboard webhook configuration first.
export { POST } from "@/app/api/webhooks/stripe/route";
