"use client";

import { signOut } from "next-auth/react";

let redirectInFlight = false;

export async function clientFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(input, init);

  if (response.status === 401 && typeof window !== "undefined" && !redirectInFlight) {
    redirectInFlight = true;
    const callbackUrl = `${window.location.pathname}${window.location.search}`;
    void signOut({
      callbackUrl: `/auth/login?callbackUrl=${encodeURIComponent(callbackUrl)}`,
    });
  }

  return response;
}
