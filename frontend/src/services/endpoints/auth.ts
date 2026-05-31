import { apiRequest } from "@/services/api-client";
import type { AuthTokens, LoginRequest, OAuthEntryResponse, RegisterRequest, UserMe } from "@/types/auth";

export const authApi = {
  register: (body: RegisterRequest) => apiRequest<UserMe>("/auth/register", { method: "POST", body, auth: false }),
  login: (body: LoginRequest) => apiRequest<AuthTokens>("/auth/login", { method: "POST", body, auth: false }),
  me: () => apiRequest<UserMe>("/auth/me", { method: "GET" }),
  refresh: (refreshToken: string) =>
    apiRequest<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      auth: false,
      retryOnUnauthorized: false
    }),
  logout: (refreshToken: string) =>
    apiRequest<{ ok: boolean }>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
      auth: false,
      retryOnUnauthorized: false
    }),
  oauthEntry: (provider: "google" | "github") => apiRequest<OAuthEntryResponse>(`/auth/${provider}`, { method: "GET", auth: false })
};
