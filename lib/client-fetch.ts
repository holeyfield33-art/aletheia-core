"use client";

import { signOut } from "next-auth/react";

let redirectInFlight = false;

export class ClientFetchError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.name = "ClientFetchError";
    this.status = status;
    this.data = data;
  }
}

export function isClientFetchError(error: unknown): error is ClientFetchError {
  return error instanceof ClientFetchError;
}

async function parseErrorResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => null);
  }
  return response.text().catch(() => null);
}

export async function clientFetchResponse(
  input: RequestInfo | URL,
  init?: RequestInit,
  timeoutMs = 10_000,
): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(input, {
      ...init,
      signal: controller.signal,
    });

    if (response.status === 401 && typeof window !== "undefined" && !redirectInFlight) {
      redirectInFlight = true;
      const callbackUrl = `${window.location.pathname}${window.location.search}`;
      void signOut({
        callbackUrl: `/auth/login?callbackUrl=${encodeURIComponent(callbackUrl)}`,
      });
      throw new Error("Session expired");
    }

    if (!response.ok) {
      const data = await parseErrorResponse(response.clone());
      throw new ClientFetchError(`HTTP ${response.status}`, response.status, data);
    }

    return response;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function clientFetch<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
  timeoutMs = 10_000,
): Promise<T> {
  const response = await clientFetchResponse(input, init, timeoutMs);
  return response.json() as Promise<T>;
}
