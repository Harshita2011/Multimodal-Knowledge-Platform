"use client";

import { API_BASE_URL } from "@/lib/env";
import { useAuthStore } from "@/stores/auth-store";
import { ApiError, type ApiErrorBody } from "@/types/api";
import type { AuthTokens } from "@/types/auth";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
  retryOnUnauthorized?: boolean;
};

let refreshPromise: Promise<AuthTokens> | null = null;

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const body = data as ApiErrorBody | null;
    throw new ApiError(
      body?.error?.message || response.statusText || "Request failed",
      response.status,
      body?.error?.code,
      body?.error?.correlation_id,
      body?.error?.details
    );
  }

  return data as T;
}

async function refreshTokens(): Promise<AuthTokens> {
  const { refreshToken, setTokens, setRefreshing, clearAuth } = useAuthStore.getState();
  if (!refreshToken) {
    clearAuth();
    throw new ApiError("Session expired", 401, "missing_refresh");
  }

  if (!refreshPromise) {
    setRefreshing(true);
    refreshPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    })
      .then((res) => parseResponse<AuthTokens>(res))
      .then((tokens) => {
        const remember = typeof window !== "undefined" && window.localStorage.getItem("mkp.remember") === "true";
        setTokens(tokens, remember);
        return tokens;
      })
      .catch((error) => {
        clearAuth();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
        setRefreshing(false);
      });
  }

  return refreshPromise;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, retryOnUnauthorized = true, headers, ...init } = options;
  const { accessToken } = useAuthStore.getState();
  const requestHeaders = new Headers(headers);

  if (!(body instanceof FormData) && body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }
  if (auth && accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: requestHeaders,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined
  });

  if (response.status === 401 && auth && retryOnUnauthorized) {
    try {
      const tokens = await refreshTokens();
      const retryHeaders = new Headers(requestHeaders);
      retryHeaders.set("Authorization", `Bearer ${tokens.access_token}`);
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        headers: retryHeaders,
        body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined
      });
      return parseResponse<T>(retryResponse);
    } catch (error) {
      throw error;
    }
  }

  return parseResponse<T>(response);
}
