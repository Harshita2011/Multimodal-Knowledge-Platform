"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth-store";

export function useRequireAuth() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const accessToken = useAuthStore((state) => state.accessToken);
  const bootstrapComplete = useAuthStore((state) => state.bootstrapComplete);

  useEffect(() => {
    if (bootstrapComplete && !accessToken && !user) {
      router.replace("/login");
    }
  }, [accessToken, bootstrapComplete, router, user]);

  return { user, isReady: bootstrapComplete && Boolean(accessToken || user) };
}
