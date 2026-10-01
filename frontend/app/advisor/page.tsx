"use client";

import Link from "next/link";
import { ArrowUpRight, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { FadeIn, ScoreRing, Spinner, STATUS, TopBar } from "@/components/ui";
import { api, type ClientSummary } from "@/lib/api";

export default function AdvisorHome() {
  const [clients, setClients] = useState<ClientSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.clients().then(setClients).catch((e) => setError(e.message));
  }, []);

  const scored = clients?.filter((c) => c.overall !== null) ?? [];
  const avg = scored.length ? Math.round(scored.reduce((s, c) => s + (c.overall ?? 0), 0) / scored.length) : null;

  return (
    <main className="min-h-screen pb-24">
      <TopBar
        right={
          <>
            <span className="hidden rounded-full bg-ink px-3 py-1 text-xs text-paper sm:inline">Advisor</span>
            <Link href="/discover" className="btn-ghost !px-4 !py-2">
              <Plus className="h-4 w-4" /> New discovery
            </Link>
          </>
        }
      />
      <div className="mx-auto max-w-6xl px-5 pt-12 sm:px-8">
        <FadeIn>
          <p className="eyebrow">Advisor workspace</p>
          <h1 className="mt-4 font-serif text-5xl">Your families</h1>
        </FadeIn>

        {error && <p className="mt-10 text-amber">{error}</p>}
        {!clients && !error && <Spinner label="Loading your families…" />}

        {clients && (
          <>
            <FadeIn delay={0.1} className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3">
              {[
                ["Relationships", clients.length.toString()],
                ["Average alignment", avg !== null ? `${avg}%` : "—"],
                ["Awaiting next step", clients.filter((c) => c.status !== "aligned").length.toString()],
              ].map(([label, value]) => (
                <div key={label} className="bg-white px-8 py-6">
                  <p className="eyebrow !text-[10px]">{label}</p>
                  <p className="mt-2 font-serif text-4xl">{value}</p>
                </div>
              ))}
            </FadeIn>

            <div className="mt-10 space-y-4">
              {clients.map((c, i) => (
                <FadeIn key={c.id} delay={0.15 + i * 0.05}>
                  <Link href={`/advisor/${c.id}`} className="card group grid items-center gap-6 p-6 transition hover:border-gold/50 sm:grid-cols-[1fr_auto_auto]">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="font-serif text-2xl">{c.name}</h2>
                        <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${STATUS[c.status].cls}`}>{STATUS[c.status].label}</span>
                        <span className="text-xs capitalize text-ink-muted">{c.household_type}</span>
                      </div>
                      <p className="mt-2 truncate font-serif text-lg italic text-ink-muted">
                        {c.purpose ? `“${c.purpose}”` : "Discovery conversation in progress"}
                      </p>
                      {c.values.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {c.values.map((v) => (
                            <span key={v} className="rounded-full border border-line px-2.5 py-0.5 text-xs text-ink-soft">
                              {v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="justify-self-start sm:justify-self-end">
                      {c.overall !== null ? <ScoreRing value={c.overall} size={76} stroke={4} /> : <div className="flex h-[76px] w-[76px] items-center justify-center rounded-full border border-dashed border-line text-xs text-ink-muted">—</div>}
                    </div>
                    <ArrowUpRight className="hidden h-5 w-5 text-ink-muted transition group-hover:text-gold sm:block" />
                  </Link>
                </FadeIn>
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
