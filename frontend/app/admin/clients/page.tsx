"use client";

import Link from "next/link";
import { ArrowLeft, KeyRound, LogOut, RefreshCw, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FadeIn, Spinner, STATUS, TopBar } from "@/components/ui";
import { api, ApiError, type AdminQa, type ClientSummary, type StaffRole } from "@/lib/api";

/** Beta administration: QA counters (never AI content), resume-link reset, and permanent deletion with a typed confirmation. */
export default function AdminClients() {
  const router = useRouter();
  const [role, setRole] = useState<StaffRole | null>(null);
  const [qa, setQa] = useState<AdminQa | null>(null);
  const [clients, setClients] = useState<ClientSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [newLink, setNewLink] = useState<{ id: number; path: string } | null>(null);
  const [confirming, setConfirming] = useState<ClientSummary | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => Promise.all([api.adminQa().then(setQa), api.clients().then(setClients)]).catch((e) => setError(e.message)), []);
  useEffect(() => {
    api.me()
      .then((r) => {
        setRole(r.role);
        if (r.role === "admin") reload();
      })
      .catch((e) => (e instanceof ApiError && e.status === 401 ? router.replace("/login?next=/admin/clients") : setError(e.message)));
  }, [reload, router]);

  async function revoke(c: ClientSummary) {
    if (!confirm(`Reset ${c.name}'s private link? Every existing link and signed-in device for this client stops working immediately.`)) return;
    setBusy(true);
    try {
      const r = await api.adminRevokeToken(c.id);
      setNewLink({ id: c.id, path: r.resume_link_path });
      setNotice(`Link reset for ${c.name}. Give them the new link below; the old one is dead.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reset");
    } finally {
      setBusy(false);
    }
  }

  async function doDelete() {
    if (!confirming) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.adminDeleteClient(confirming.id, typed.trim());
      setNotice(`Deleted ${confirming.name}: ${Object.entries(r.removed).map(([k, v]) => `${v} ${k}`).join(", ")}.`);
      setConfirming(null);
      setTyped("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete");
    } finally {
      setBusy(false);
    }
  }

  if (role === "advisor") {
    return (
      <main className="min-h-screen">
        <TopBar right={<Link href="/advisor" className="btn-ghost !px-4 !py-2"><ArrowLeft className="h-4 w-4" /> Advisor</Link>} />
        <div className="mx-auto max-w-xl px-5 py-24 text-center sm:px-8">
          <p className="eyebrow">Admin only</p>
          <h1 className="mt-3 font-serif text-3xl">Beta administration needs the admin password.</h1>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-24">
      <TopBar
        right={
          <>
            <span className="hidden rounded-full bg-ink px-3 py-1 text-xs text-paper sm:inline">Admin</span>
            <Link href="/admin/methodology" className="btn-ghost !px-4 !py-2">Methodology</Link>
            <Link href="/advisor" className="btn-ghost !px-4 !py-2"><ArrowLeft className="h-4 w-4" /> Advisor</Link>
            <button onClick={() => api.logout().then(() => router.replace("/login"))} className="btn-ghost !px-4 !py-2" aria-label="Sign out"><LogOut className="h-4 w-4" /></button>
          </>
        }
      />
      {qa && (
        <div className={`${qa.demo_mode ? "bg-amber text-white" : "bg-sage text-white"} px-5 py-2 text-center text-xs uppercase tracking-eyebrow`}>
          {qa.demo_mode ? "Demo mode — stand-in AI. Not for real beta users." : `Live model · ${qa.model} · ${qa.app_env}`}
        </div>
      )}
      <div className="mx-auto max-w-5xl px-5 pt-12 sm:px-8">
        <FadeIn>
          <p className="eyebrow">Beta administration</p>
          <h1 className="mt-4 font-serif text-5xl">Quality &amp; clients</h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
            Counters only. Items the AI produced that failed validation are discarded, never stored and never shown to anyone;
            the counts below exist to tune prompts. Error counters reset when the backend restarts.
          </p>
        </FadeIn>
        {error && <p className="mt-6 text-sm text-amber">{error}</p>}
        {notice && <p className="mt-6 rounded-xl border border-sage/40 bg-sage/5 px-4 py-3 text-sm text-ink-soft">{notice}</p>}
        {!qa && !error && <Spinner label="Loading…" />}
        {qa && (
          <FadeIn delay={0.05} className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-4">
            {[
              ["Discoveries", qa.sessions], ["Completed", qa.completed], ["Shared with advisor", qa.shared_with_advisor], ["Abandoned (start fresh)", qa.abandoned],
              ["Insights (active)", qa.insights_total], ["Need clarification", qa.needs_clarification_count], ["AI items rejected", qa.rejected_insight_count], ["Extraction runs", qa.extraction_runs],
              ["Model errors", qa.model_errors], ["Extraction failures", qa.extraction_failures], ["Rate-limit hits", qa.rate_limited], ["Mode", qa.demo_mode ? "demo" : "live"],
            ].map(([l, v]) => (
              <div key={String(l)} className="bg-white px-5 py-4">
                <p className="eyebrow !text-[10px]">{l}</p>
                <p className="mt-1 font-serif text-3xl">{v}</p>
              </div>
            ))}
          </FadeIn>
        )}
        {qa && Object.keys(qa.last).length > 0 && (
          <p className="mt-3 text-[11px] text-ink-muted">
            Last: {Object.entries(qa.last).map(([k, v]) => `${k} — ${v.detail} (${new Date(v.at * 1000).toLocaleString()})`).join(" · ")}
          </p>
        )}

        <div className="mt-14">
          <p className="eyebrow">Clients</p>
          <div className="rule mt-2" />
          {newLink && (
            <div className="card mt-6 border-gold/40 bg-gold-pale/10 p-5 text-sm">
              <p className="eyebrow !text-[10px]">New private link for client #{newLink.id} — shown once, give it to the client directly</p>
              <code className="mt-2 block select-all break-all rounded-lg bg-white px-3 py-2 text-xs">{typeof window !== "undefined" ? window.location.origin : ""}{newLink.path}</code>
            </div>
          )}
          <div className="mt-6 space-y-3">
            {clients?.map((c) => (
              <div key={c.id} className="card flex flex-wrap items-center justify-between gap-4 p-5">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-serif text-xl">{c.name}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${STATUS[c.status].cls}`}>{STATUS[c.status].label}</span>
                    <span className="rounded-full bg-cream px-2.5 py-0.5 text-[11px] text-ink-muted">{c.sharing === "legacy" ? "demo family" : c.sharing.replace(/_/g, " ")}</span>
                  </div>
                  <p className="mt-1 text-xs text-ink-muted">#{c.id} · last activity {new Date(c.last_activity_at).toLocaleString()}</p>
                </div>
                <div className="flex gap-2">
                  {c.sharing !== "legacy" && (
                    <button onClick={() => revoke(c)} disabled={busy} className="btn-ghost !px-3 !py-1.5 !text-xs"><KeyRound className="h-3.5 w-3.5" /> Reset link</button>
                  )}
                  <button onClick={() => { setConfirming(c); setTyped(""); }} disabled={busy} className="btn-ghost !px-3 !py-1.5 !text-xs hover:!border-amber hover:!text-amber"><Trash2 className="h-3.5 w-3.5" /> Delete data</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {confirming && (
          <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/60 p-5">
            <div className="card w-full max-w-md p-8">
              <p className="eyebrow !text-amber">Permanent deletion</p>
              <h2 className="mt-2 font-serif text-2xl">Delete everything about {confirming.name}?</h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-muted">
                Removes their answers, insights, evidence, feedback history, purpose statements, scores, notes, session and resume token.
                This cannot be undone. Type the client&apos;s name to confirm.
              </p>
              <input autoFocus value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={confirming.name} className="mt-4 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-amber" />
              <div className="mt-4 flex gap-2">
                <button onClick={doDelete} disabled={busy || typed.trim().toLowerCase() !== confirming.name.trim().toLowerCase()} className="btn-primary !bg-amber !py-2 disabled:!opacity-40">
                  <Trash2 className="h-4 w-4" /> Delete permanently
                </button>
                <button onClick={() => setConfirming(null)} className="btn-ghost !py-2">Cancel</button>
              </div>
            </div>
          </div>
        )}
        <p className="mt-10 text-[11px] text-ink-muted/70"><RefreshCw className="mr-1 inline h-3 w-3" /> Counters refresh on page load.</p>
      </div>
    </main>
  );
}
