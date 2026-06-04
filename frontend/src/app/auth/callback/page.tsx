"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { authApi } from "@/services/endpoints/auth";
import { useAuthStore } from "@/stores/auth-store";
import type { AuthTokens } from "@/types/auth";

type QueryParams = {
  get: (name: string) => string | null;
};

function getTokensFromParams(searchParams: QueryParams): AuthTokens | null {
  const accessToken = searchParams.get("access_token");
  const refreshToken = searchParams.get("refresh_token");

  if (!accessToken || !refreshToken) {
    return null;
  }

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    token_type: "bearer"
  };
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTokens = useAuthStore((state) => state.setTokens);
  const setUser = useAuthStore((state) => state.setUser);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tokens = getTokensFromParams(searchParams);

    if (!tokens) {
      setError("Missing OAuth tokens in callback URL.");
      return;
    }

    let isActive = true;

    (async () => {
      try {
        setTokens(tokens, true);
        const user = await authApi.me();
        if (!isActive) return;
        setUser(user);
        router.replace("/dashboard");
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "OAuth sign-in failed.");
      }
    })();

    return () => {
      isActive = false;
    };
  }, [router, searchParams, setTokens, setUser]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="flex flex-col items-center gap-4 rounded-xl border bg-card px-8 py-10 text-center shadow-sm">
        {!error ? <Loader2 className="h-6 w-6 animate-spin text-primary" /> : null}
        <div className="space-y-2">
          <h1 className="text-xl font-semibold">{error ? "Sign-in failed" : "Completing sign-in"}</h1>
          <p className="max-w-sm text-sm text-muted-foreground">
            {error
              ? error
              : "We are saving your session and moving you into the app."}
          </p>
        </div>
        {error ? (
          <button
            className="text-sm font-medium text-primary hover:underline"
            onClick={() => router.replace("/login")}
            type="button"
          >
            Back to login
          </button>
        ) : null}
      </div>
    </div>
  );
}
