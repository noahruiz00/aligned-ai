"use client";

import { ArrowRight, Lock } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { FadeIn, TopBar } from "@/components/ui";
import { api } from "@/lib/api";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen"><TopBar /></main>}>
      <Login />
    </Suspense>
  );
}

function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const next = params.get("next") || "/advisor";
  const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/advisor";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.login(password);
      router.replace(safeNext.startsWith("/admin") && r.role !== "admin" ? "/advisor" : safeNext);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen">
      <TopBar />
      <div className="mx-auto max-w-md px-5 py-24 sm:px-8">
        <FadeIn>
          <Lock className="h-6 w-6 text-gold" strokeWidth={1.5} />
          <p className="eyebrow mt-6">Private beta</p>
          <h1 className="mt-3 font-serif text-4xl">Advisor sign in</h1>
          <p className="mt-3 text-sm text-ink-muted">This area is for the advisory team. Clients don&apos;t need an account: their private link is their key.</p>
        </FadeIn>
        <FadeIn delay={0.1}>
          <form onSubmit={submit} className="card mt-8 space-y-6 p-8">
            <label className="block">
              <span className="eyebrow">Password</span>
              <input
                autoFocus
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-3 w-full border-b border-line bg-transparent pb-2 font-serif text-2xl outline-none transition focus:border-gold"
              />
            </label>
            <button type="submit" disabled={!password || busy} className="btn-primary w-full">
              {busy ? "Signing in…" : "Sign in"} <ArrowRight className="h-4 w-4" />
            </button>
            {error && <p className="text-sm text-amber">{error}</p>}
          </form>
        </FadeIn>
      </div>
    </main>
  );
}
