"use client";

import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { authApi } from "@/services/endpoints/auth";
import { useAuthStore } from "@/stores/auth-store";

export default function SettingsPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  async function logout() {
    if (refreshToken) await authApi.logout(refreshToken).catch(() => undefined);
    clearAuth();
    router.replace("/login");
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage account, session, and local display preferences.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="h-4 w-4" />
              Profile
            </CardTitle>
            <CardDescription>Read from /auth/me</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between gap-3 border-b pb-3">
              <span className="text-muted-foreground">Name</span>
              <span className="font-medium">{user?.name || "Not set"}</span>
            </div>
            <div className="flex justify-between gap-3 border-b pb-3">
              <span className="text-muted-foreground">Email</span>
              <span className="font-medium">{user?.email}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Provider</span>
              <Badge>{user?.provider || "password"}</Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              Security
            </CardTitle>
            <CardDescription>Session actions for this browser</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">Logout revokes the current refresh token on the backend and clears local session state.</p>
            <Button variant="destructive" onClick={logout}>
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Stored locally in this browser</CardDescription>
          </CardHeader>
          <CardContent>
            <ThemeToggle />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
