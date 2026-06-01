"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard } from "@/features/auth/components/auth-card";
import { signupSchema, type SignupFormValues } from "@/features/auth/schemas/auth-schemas";
import { authApi } from "@/services/endpoints/auth";

export default function SignupPage() {
  const router = useRouter();
  const form = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { name: "", email: "", password: "", terms: false }
  });

  async function onSubmit(values: SignupFormValues) {
    try {
      await authApi.register({ email: values.email, password: values.password, name: values.name || null });
      router.replace("/login");
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : "Signup failed"
      });
    }
  }

  return (
    <AuthCard title="Create your workspace" description="Set up access to upload PDFs, ask questions, and review cited answers.">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        {form.formState.errors.root ? <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{form.formState.errors.root.message}</p> : null}
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" autoComplete="name" {...form.register("name")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          {form.formState.errors.email ? <p className="text-xs text-destructive">{form.formState.errors.email.message}</p> : null}
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" {...form.register("password")} />
          {form.formState.errors.password ? <p className="text-xs text-destructive">{form.formState.errors.password.message}</p> : null}
        </div>
        <label className="flex items-start gap-2 text-sm text-muted-foreground">
          <input className="mt-0.5 h-4 w-4 rounded border" type="checkbox" {...form.register("terms")} />
          I agree to use this workspace for documents I am allowed to process.
        </label>
        {form.formState.errors.terms ? <p className="text-xs text-destructive">{form.formState.errors.terms.message}</p> : null}
        <Button className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Create account
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link className="font-medium text-primary hover:underline" href="/login">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
