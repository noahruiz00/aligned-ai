"use client";

import Link from "next/link";
import { AlertTriangle, ArrowLeft, Check, ChevronDown, FileText, MessageCircle, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { CategoryCards, ScoreSummary } from "@/components/ScoreBreakdown";
import { FadeIn, RichText, Spinner, STATUS, TopBar, ValueIcon } from "@/components/ui";
import { api, type AdvisorClientDetail } from "@/lib/api";

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="eyebrow !text-[10px]">{title}</p>
      <ul className="mt-2 space-y-1.5">
        {items.map((x) => (
          <li key={x} className="text-sm leading-relaxed text-ink-soft">
            {x}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AdvisorClient({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [d, setD] = useState<AdvisorClientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [showTranscript, setShowTranscript] = useState(false);

  useEffect(() => {
    api.client(id).then(setD).catch((e) => setError(e.message));
  }, [id]);

  async function addNote(e: FormEvent) {
    e.preventDefault();
    if (!note.trim() || !d) return;
    const n = await api.addNote(id, note.trim());
    setD({ ...d, notes: [n, ...d.notes] });
    setNote("");
  }

  return (
    <main className="min-h-screen pb-24">
      <TopBar
        right={
          <>
            <span className="hidden rounded-full bg-ink px-3 py-1 text-xs text-paper sm:inline">Advisor</span>
            <Link href="/advisor" className="btn-ghost !px-4 !py-2">
              <ArrowLeft className="h-4 w-4" /> All families
            </Link>
          </>
        }
      />
      {error && <p className="p-10 text-center text-amber">{error}</p>}
      {!d && !error && <Spinner label="Preparing the client brief…" />}
      {d && (
        <div className="mx-auto grid max-w-6xl gap-10 px-5 pt-12 sm:px-8 lg:grid-cols-[1fr_340px]">
          {/* Main column */}
          <div className="min-w-0 space-y-10">
            <FadeIn>
              <div className="flex flex-wrap items-center gap-3">
                <p className="eyebrow">Client brief</p>
                <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${STATUS[d.user.status].cls}`}>{STATUS[d.user.status].label}</span>
              </div>
              <h1 className="mt-3 font-serif text-5xl">{d.user.name}</h1>
              <p className="mt-1 text-sm capitalize text-ink-muted">{d.user.household_type}</p>
              {d.purpose && (
                <div className="mt-8 border-l-2 border-gold pl-6">
                  <p className="eyebrow !text-[10px]">Wealth purpose</p>
                  <p className="mt-2 font-serif text-2xl leading-snug italic text-ink-soft">“{d.purpose.purpose_statement}”</p>
                  <Link href={`/client/${id}/statement`} className="mt-3 inline-flex items-center gap-1.5 text-sm text-gold-deep hover:underline">
                    <FileText className="h-3.5 w-3.5" /> Full Wealth Purpose Statement
                  </Link>
                </div>
              )}
            </FadeIn>

            {d.insights && (
              <FadeIn delay={0.1} className="card overflow-hidden">
                <div className="flex items-center justify-between gap-4 border-b border-line bg-ink px-8 py-5 text-paper">
                  <div className="flex items-center gap-3">
                    <Sparkles className="h-4 w-4 text-gold-light" strokeWidth={1.5} />
                    <span className="eyebrow !text-gold-light">AI insights · Meeting preparation</span>
                  </div>
                  <span className="hidden text-[11px] text-paper/50 sm:inline">Supports your judgement. Not client advice.</span>
                </div>
                <div className="space-y-8 p-8">
                  <p className="font-serif text-xl leading-relaxed text-ink-soft">{d.insights.summary}</p>
                  <div className="grid gap-8 md:grid-cols-2">
                    <div className="space-y-3">
                      {d.insights.strengths.map((s) => (
                        <div key={s} className="flex gap-3 text-sm leading-relaxed">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-sage" />
                          <span className="text-ink-soft">{s}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-3">
                      {d.insights.gaps.map((g) => (
                        <div key={g} className="flex gap-3 text-sm leading-relaxed">
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
                          <span className="text-ink-soft">{g}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="grid gap-8 border-t border-line pt-8 md:grid-cols-2">
                    <div>
                      <p className="eyebrow !text-[10px]">Recommended conversation</p>
                      <ul className="mt-3 space-y-3">
                        {d.insights.conversation_starters.map((q) => (
                          <li key={q} className="flex gap-3 font-serif text-lg italic leading-snug text-ink-soft">
                            <MessageCircle className="mt-1 h-4 w-4 shrink-0 text-gold" strokeWidth={1.5} />
                            {q}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="eyebrow !text-[10px]">Next meeting agenda</p>
                      <ol className="mt-3 space-y-2">
                        {d.insights.meeting_agenda.map((a, i) => (
                          <li key={a} className="flex gap-3 text-sm text-ink-soft">
                            <span className="font-serif text-gold">{i + 1}.</span> {a}
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                </div>
              </FadeIn>
            )}

            {d.score ? (
              <>
                <FadeIn delay={0.15}>
                  <ScoreSummary score={d.score} compact />
                </FadeIn>
                <CategoryCards score={d.score} audience="advisor" />
              </>
            ) : (
              <div className="card p-8 text-sm text-ink-muted">
                {d.purpose
                  ? "The client has a Wealth Purpose Statement but hasn't completed their financial portrait yet, so no alignment score is available."
                  : "The client is still in their discovery conversation."}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            {d.values && (
              <FadeIn delay={0.1} className="card space-y-6 p-6">
                <p className="eyebrow">Values profile</p>
                <div className="space-y-3">
                  {d.values.values.map((v) => (
                    <div key={v.name} className="flex gap-3">
                      <span className="mt-0.5 text-gold-deep">
                        <ValueIcon name={v.name} className="h-4 w-4" />
                      </span>
                      <div>
                        <p className="text-sm font-medium">{v.name}</p>
                        <p className="text-xs leading-relaxed text-ink-muted">{v.why}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <List title="Financial priorities" items={d.values.financial_priorities} />
                <List title="Philanthropic interests" items={d.values.philanthropy} />
                <List title="Family goals" items={d.values.family_goals} />
                <List title="Emotional cues" items={d.values.emotional_cues} />
                {d.values.money_script && (
                  <div>
                    <p className="eyebrow !text-[10px]">Money script</p>
                    <p className="mt-2 font-serif text-base italic leading-relaxed text-ink-soft">{d.values.money_script}</p>
                  </div>
                )}
              </FadeIn>
            )}

            <FadeIn delay={0.15} className="card p-6">
              <p className="eyebrow">Advisor notes</p>
              <form onSubmit={addNote} className="mt-4">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={3}
                  placeholder="Add a private note…"
                  className="w-full resize-none rounded-xl border border-line bg-paper p-3 text-sm outline-none focus:border-gold/60"
                />
                <button disabled={!note.trim()} className="btn-primary mt-2 w-full !py-2">
                  Save note
                </button>
              </form>
              <div className="mt-5 space-y-4">
                {d.notes.map((n) => (
                  <div key={n.id} className="border-t border-line pt-3">
                    <p className="text-sm leading-relaxed text-ink-soft">{n.body}</p>
                    <p className="mt-1 text-[11px] text-ink-muted">{new Date(n.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            </FadeIn>

            {d.transcript.length > 0 && (
              <div className="card p-6">
                <button onClick={() => setShowTranscript((s) => !s)} className="flex w-full items-center justify-between">
                  <span className="eyebrow">Discovery transcript</span>
                  <ChevronDown className={`h-4 w-4 text-ink-muted transition ${showTranscript ? "rotate-180" : ""}`} />
                </button>
                {showTranscript && (
                  <div className="mt-5 max-h-[480px] space-y-4 overflow-y-auto pr-1">
                    {d.transcript.map((m, i) => (
                      <div key={i} className={`text-sm leading-relaxed ${m.role === "user" ? "text-ink" : "text-ink-muted"}`}>
                        <p className="eyebrow mb-1 !text-[9px]">{m.role === "user" ? d.user.name.split(" ")[0] : "Aligned"}</p>
                        <RichText text={m.content} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      )}
    </main>
  );
}
