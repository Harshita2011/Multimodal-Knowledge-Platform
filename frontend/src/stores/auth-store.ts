"use client";

import { create } from "zustand";
import type { AuthTokens, UserMe } from "@/types/auth";

const ACCESS_TOKEN_KEY = "mkp.access";
const REFRESH_TOKEN_KEY = "mkp.refresh";
const PERSIST_KEY = "mkp.remember";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserMe | null;
  bootstrapComplete: boolean;
  isRefreshing: boolean;
  hydrate: () => void;
  setTokens: (tokens: AuthTokens, remember: boolean) => void;
  setUser: (user: UserMe | null) => void;
  setBootstrapComplete: (value: boolean) => void;
  setRefreshing: (value: boolean) => void;
  clearAuth: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  bootstrapComplete: false,
  isRefreshing: false,
  hydrate: () => {
    if (typeof window === "undefined") return;
    const remember = window.localStorage.getItem(PERSIST_KEY) === "true";
    const source = remember ? window.localStorage : window.sessionStorage;
    set({
      accessToken: source.getItem(ACCESS_TOKEN_KEY),
      refreshToken: source.getItem(REFRESH_TOKEN_KEY)
    });
  },
  setTokens: (tokens, remember) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(PERSIST_KEY, remember ? "true" : "false");
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
      window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
      const target = remember ? window.localStorage : window.sessionStorage;
      target.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      target.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    }
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setUser: (user) => set({ user }),
  setBootstrapComplete: (bootstrapComplete) => set({ bootstrapComplete }),
  setRefreshing: (isRefreshing) => set({ isRefreshing }),
  clearAuth: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
      window.localStorage.removeItem(PERSIST_KEY);
      window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    }
    set({ accessToken: null, refreshToken: null, user: null, bootstrapComplete: true, isRefreshing: false });
  }
}));
