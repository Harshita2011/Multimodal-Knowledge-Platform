"use client";

import type { ReactNode } from "react";
import { AuthBootstrap } from "@/providers/auth-bootstrap";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <AuthBootstrap>{children}</AuthBootstrap>
      </QueryProvider>
    </ThemeProvider>
  );
}
