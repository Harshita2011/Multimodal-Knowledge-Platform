"use client";

import type { ReactNode } from "react";
import { WorkspaceShell } from "@/components/layout/workspace-shell";
import { useRequireAuth } from "@/hooks/use-require-auth";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const { isReady } = useRequireAuth();

  if (!isReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Preparing workspace...
      </div>
    );
  }

  return <WorkspaceShell>{children}</WorkspaceShell>;
}
