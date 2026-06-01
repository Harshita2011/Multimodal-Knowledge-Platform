"use client";

import { BarChart3, FileUp, LogOut, MessageSquareText, PanelLeftClose, PanelLeftOpen, Settings, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { cn, initials } from "@/lib/utils";
import { authApi } from "@/services/endpoints/auth";
import { useAuthStore } from "@/stores/auth-store";
import { useUiStore } from "@/stores/ui-store";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/chat", label: "Chat", icon: MessageSquareText },
  { href: "/upload", label: "Upload", icon: FileUp },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const setCollapsed = useUiStore((state) => state.setSidebarCollapsed);

  async function logout() {
    if (refreshToken) {
      await authApi.logout(refreshToken).catch(() => undefined);
    }
    clearAuth();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden border-r bg-card transition-all duration-200 lg:flex lg:flex-col",
          collapsed ? "w-20" : "w-72"
        )}
      >
        <div className="flex h-16 items-center gap-3 border-b px-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
            MK
          </div>
          {!collapsed ? (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">Knowledge Platform</p>
              <p className="truncate text-xs text-muted-foreground">Grounded multimodal RAG</p>
            </div>
          ) : null}
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                className={cn(
                  "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  active && "bg-primary/10 text-primary",
                  collapsed && "justify-center px-0"
                )}
                href={item.href}
                title={item.label}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed ? item.label : null}
              </Link>
            );
          })}
        </nav>
        <div className="border-t p-3">
          <div className={cn("mb-3 flex items-center gap-3 rounded-md bg-muted p-3", collapsed && "justify-center p-2")}>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-background text-xs font-semibold">
              {initials(user?.name, user?.email)}
            </div>
            {!collapsed ? (
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user?.name || "User"}</p>
                <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
              </div>
            ) : null}
          </div>
          <Button className={cn("w-full", collapsed && "px-0")} variant="ghost" onClick={logout} title="Logout">
            <LogOut className="h-4 w-4" />
            {!collapsed ? "Logout" : null}
          </Button>
        </div>
      </aside>
      <div className={cn("transition-all duration-200 lg:pl-72", collapsed && "lg:pl-20")}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur md:px-6">
          <div className="flex items-center gap-3">
            <Button className="hidden lg:inline-flex" size="icon" variant="ghost" onClick={() => setCollapsed(!collapsed)} title="Toggle sidebar">
              {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </Button>
            <div className="lg:hidden">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
                MK
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold">Multimodal Knowledge Platform</p>
              <p className="hidden text-xs text-muted-foreground sm:block">PDF RAG today, multimodal-ready tomorrow</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="secondary">
              <Link href="/chat">
                <Sparkles className="h-4 w-4" />
                New chat
              </Link>
            </Button>
            <ThemeToggle />
          </div>
        </header>
        <nav className="grid grid-cols-4 border-b bg-card lg:hidden">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                className={cn("flex flex-col items-center gap-1 px-2 py-2 text-xs text-muted-foreground", active && "text-primary")}
                href={item.href}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <main className="px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  );
}
