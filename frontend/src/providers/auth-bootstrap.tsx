"use client";

import { useEffect, type ReactNode } from "react";
import { authApi } from "@/services/endpoints/auth";
import { useAuthStore } from "@/stores/auth-store";

export function AuthBootstrap({ children }: { children: ReactNode }) {
  const hydrate = useAuthStore((state) => state.hydrate);
  const setUser = useAuthStore((state) => state.setUser);
  const setBootstrapComplete = useAuthStore((state) => state.setBootstrapComplete);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  useEffect(() => {
    hydrate();
    const token = useAuthStore.getState().accessToken;
    if (!token) {
      setBootstrapComplete(true);
      return;
    }

    authApi
      .me()
      .then(setUser)
      .catch(() => clearAuth())
      .finally(() => setBootstrapComplete(true));
  }, [clearAuth, hydrate, setBootstrapComplete, setUser]);

  return children;
}
