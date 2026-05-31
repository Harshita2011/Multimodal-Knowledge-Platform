"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Github, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard } from "@/features/auth/components/auth-card";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas/auth-schemas";
import { authApi } from "@/services/endpoints/auth";
import { useAuthStore } from "@/stores/auth-store";

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((state) => state.setTokens);
  const setUser = useAuthStore((state) => state.setUser);
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", remember: true }
  });

  async function onSubmit(values: LoginFormValues) {
    try {
      const tokens = await authApi.login({ email: values.email, password: values.password });
      setTokens(tokens, values.remember);
      const user = await authApi.me();
      setUser(user);
      router.replace("/dashboard");
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : "Login failed"
      });
    }
  }

  async function startOAuth(provider: "google" | "github") {
    try {
      const entry = await authApi.oauthEntry(provider);
      window.location.href = entry.authorization_url;
    } catch (error) {
      form.setError("root", {
        message:
          error instanceof Error
            ? error.message
            : "OAuth is not configured yet. Please use email and password."
      });
    }
  }

  return (
    <AuthCard title="Welcome back" description="Sign in to continue working with your grounded knowledge assistant.">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        {form.formState.errors.root ? <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{form.formState.errors.root.message}</p> : null}
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          {form.formState.errors.email ? <p className="text-xs text-destructive">{form.formState.errors.email.message}</p> : null}
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" {...form.register("password")} />
          {form.formState.errors.password ? <p className="text-xs text-destructive">{form.formState.errors.password.message}</p> : null}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input className="h-4 w-4 rounded border" type="checkbox" {...form.register("remember")} />
          Remember this session
        </label>
        <Button className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Sign in
        </Button>
      </form>
      <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        OAuth
        <div className="h-px flex-1 bg-border" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Button variant="outline" type="button" onClick={() => startOAuth("google")}>
          G Google
        </Button>
        <Button variant="outline" type="button" onClick={() => startOAuth("github")}>
          <Github className="h-4 w-4" /> GitHub
        </Button>
      </div>
      <p className="mt-3 text-center text-xs text-muted-foreground">
        OAuth requires provider credentials on the backend. Email/password works for local development.
      </p>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link className="font-medium text-primary hover:underline" href="/signup">
          Create an account
        </Link>
      </p>
    </AuthCard>
  );
}
