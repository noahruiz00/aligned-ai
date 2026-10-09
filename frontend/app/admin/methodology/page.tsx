"use client";

import Link from "next/link";
import { ArrowDown, ArrowLeft, ArrowUp, LogOut, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FadeIn, Spinner, TopBar } from "@/components/ui";
import { api, ApiError, type AdminQa, type Classification, type MethodologyModule, type MethodologyQuestion, type StaffRole } from "@/lib/api";

const CLASS_LABEL: Record<Classification, string> = {
  core: "Core · asked in the main flow",
  follow_up: "Follow-up · the AI may ask it after a core question in this section",
  optional: "Optional · offered as “go deeper” after the module",
  inactive: "Inactive · kept, never shown",
};
const CLASS_BADGE: Record<Classification, string> = {
  core: "bg-ink text-paper",
  follow_up: "bg-gold-pale/70 text-gold-deep",
  optional: "border border-line text-ink-muted",
  inactive: "bg-cream text-ink-muted/60 line-through",
};

/** The advisor's methodology editor. Everything here is data in the backend; nothing is hard-coded in the client flow. */
export default function MethodologyAdmin() {
  const router = useRouter();
  const [modules, setModules] = useState<MethodologyModule[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [role, setRole] = useState<StaffRole | null>(null);
  const [qa, setQa] = useState<AdminQa | null>(null);

  const reload = useCallback(() => api.adminMethodology().then(setModules).catch((e) => setError(e.message)), []);
  useEffect(() => {
    api.me()
      .then((r) => {
        setRole(r.role);
        if (r.role === "admin") {
          reload();
          api.adminQa().then(setQa).catch(() => undefined);
        }
      })
      .catch((e) => (e instanceof ApiError && e.status === 401 ? router.replace("/login?next=/admin/methodology") : setError(e.message)));
  }, [reload, router]);

  if (role === "advisor") {
    return (
      <main className="min-h-screen">
        <TopBar right={<Link href="/advisor" className="btn-ghost !px-4 !py-2"><ArrowLeft className="h-4 w-4" /> Advisor</Link>} />
        <div className="mx-auto max-w-xl px-5 py-24 text-center sm:px-8">
          <p className="eyebrow">Admin only</p>
          <h1 className="mt-3 font-serif text-3xl">The methodology editor needs the admin password.</h1>
          <p className="mt-3 text-sm text-ink-muted">You are signed in as an advisor. Sign out and back in with the admin password to edit questions.</p>
        </div>
      </main>
    );
  }

  async function act(fn: () => Promise<unknown>) {
    setSaving(true);
    setError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  function moveModule(i: number, dir: -1 | 1) {
    if (!modules) return;
    const ids = modules.map((m) => m.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    act(() => api.reorder("modules", ids));
  }

  function moveQuestion(m: MethodologyModule, i: number, dir: -1 | 1) {
    const ids = m.questions.map((q) => q.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    act(() => api.reorder("questions", ids));
  }

  return (
    <main className="min-h-screen pb-24">
      <TopBar
        right={
          <>
            <span className="hidden rounded-full bg-ink px-3 py-1 text-xs text-paper sm:inline">Admin</span>
            <Link href="/advisor" className="btn-ghost !px-4 !py-2">
              <ArrowLeft className="h-4 w-4" /> Advisor
            </Link>
            <button onClick={() => api.logout().then(() => router.replace("/login"))} className="btn-ghost !px-4 !py-2" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </>
        }
      />
      {qa && (
        <div className={`${qa.demo_mode ? "bg-amber text-white" : "bg-sage text-white"} px-5 py-2 text-center text-xs uppercase tracking-eyebrow`}>
          {qa.demo_mode ? "Demo mode — stand-in AI. Not for real beta users." : `Live model · ${qa.model} · ${qa.app_env}`}
        </div>
      )}
      <div className="mx-auto max-w-4xl px-5 pt-12 sm:px-8">
        {qa && (
          <div className="mb-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-4">
            {[["Discoveries", qa.sessions], ["Completed", qa.completed], ["Shared with advisor", qa.shared_with_advisor], ["AI items rejected (QA)", qa.rejected_insight_count]].map(([l, v]) => (
              <div key={String(l)} className="bg-white px-5 py-4">
                <p className="eyebrow !text-[10px]">{l}</p>
                <p className="mt-1 font-serif text-3xl">{v}</p>
              </div>
            ))}
          </div>
        )}
        <FadeIn>
          <p className="eyebrow">Methodology editor</p>
          <h1 className="mt-4 font-serif text-5xl">Discovery questions</h1>
          <p className="mt-4 max-w-2xl leading-relaxed text-ink-muted">
            Clients see active modules in this order, one question at a time. Only <strong>core</strong> questions are asked by default;
            <strong> follow-up</strong> questions are what the AI may ask after a core question in the same section, in your wording;
            <strong> optional</strong> questions are offered as “go deeper” after each module. Changes save as you leave each field.
          </p>
        </FadeIn>
        {modules && (
          <FadeIn delay={0.05} className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-5">
            {(["core", "follow_up", "optional", "inactive"] as Classification[]).map((c) => (
              <div key={c} className="bg-white px-5 py-4">
                <p className="eyebrow !text-[10px]">{c.replace("_", "-")}</p>
                <p className="mt-1 font-serif text-3xl">{modules.reduce((n, m) => n + m.questions.filter((q) => q.classification === c).length, 0)}</p>
              </div>
            ))}
            <div className="bg-white px-5 py-4">
              <p className="eyebrow !text-[10px] !text-amber">For review</p>
              <p className="mt-1 font-serif text-3xl">{modules.reduce((n, m) => n + m.questions.filter((q) => q.flags && q.flags.length).length, 0)}</p>
              <p className="text-[11px] text-ink-muted">duplicates &amp; possible typos</p>
            </div>
          </FadeIn>
        )}
        {error && <p className="mt-6 text-sm text-amber">{error}</p>}
        {!modules && !error && <Spinner label="Loading the methodology…" />}
        {modules && (
          <div className="mt-10 space-y-6">
            {modules.map((m, i) => (
              <ModuleCard
                key={m.id}
                m={m}
                index={i}
                count={modules.length}
                saving={saving}
                onSave={(body) => act(() => api.updateModule(m.id, body))}
                onDelete={() => confirm(`Remove "${m.title}"? If clients have answered its questions it will be deactivated instead.`) && act(() => api.deleteModule(m.id))}
                onMove={(dir) => moveModule(i, dir)}
                onSaveQuestion={(qid, body) => act(() => api.updateQuestion(qid, body))}
                onDeleteQuestion={(q) => confirm(`Remove this question?${q.answer_count ? " It has answers, so it will be deactivated instead." : ""}`) && act(() => api.deleteQuestion(q.id))}
                onMoveQuestion={(qi, dir) => moveQuestion(m, qi, dir)}
                onAddQuestion={(prompt) => act(() => api.createQuestion({ module_id: m.id, prompt }))}
              />
            ))}
            <AddModule onAdd={(title) => act(() => api.createModule({ title }))} saving={saving} />
          </div>
        )}
      </div>
    </main>
  );
}

function Field({ label, value, onSave, rows = 2, mono = false }: { label: string; value: string; onSave: (v: string) => void; rows?: number; mono?: boolean }) {
  const [v, setV] = useState(value);
  useEffect(() => setV(value), [value]);
  return (
    <label className="block">
      <span className="eyebrow !text-[10px]">{label}</span>
      <textarea
        value={v}
        rows={rows}
        onChange={(e) => setV(e.target.value)}
        onBlur={() => v !== value && onSave(v)}
        className={`mt-1.5 w-full resize-y rounded-xl border border-line bg-paper px-3 py-2 text-sm leading-relaxed outline-none focus:border-gold/60 ${mono ? "font-serif text-base" : ""}`}
      />
    </label>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" onClick={() => onChange(!value)} className="inline-flex items-center gap-2 text-xs text-ink-soft">
      <span className={`relative h-5 w-9 shrink-0 rounded-full transition ${value ? "bg-gold" : "bg-line"}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${value ? "left-[18px]" : "left-0.5"}`} />
      </span>
      {label}
    </button>
  );
}

function ModuleCard({ m, index, count, saving, onSave, onDelete, onMove, onSaveQuestion, onDeleteQuestion, onMoveQuestion, onAddQuestion }: {
  m: MethodologyModule;
  index: number;
  count: number;
  saving: boolean;
  onSave: (body: Partial<MethodologyModule>) => void;
  onDelete: () => void;
  onMove: (dir: -1 | 1) => void;
  onSaveQuestion: (qid: number, body: Partial<MethodologyQuestion>) => void;
  onDeleteQuestion: (q: MethodologyQuestion) => void;
  onMoveQuestion: (qi: number, dir: -1 | 1) => void;
  onAddQuestion: (prompt: string) => void;
}) {
  const [open, setOpen] = useState(index === 0);
  const [newPrompt, setNewPrompt] = useState("");
  return (
    <FadeIn className={`card overflow-hidden ${m.active ? "" : "opacity-60"}`}>
      <div className="flex items-start justify-between gap-4 p-6">
        <button onClick={() => setOpen((o) => !o)} className="min-w-0 flex-1 text-left">
          <p className="eyebrow !text-[10px]">
            Step {index + 1} · {m.description || "Module"} · Session {m.session_group} · {new Set(m.questions.map((q) => q.section).filter(Boolean)).size} sections ·{" "}
            {m.questions.filter((q) => q.classification === "core").length} core / {m.questions.filter((q) => q.classification === "follow_up").length} follow-up /{" "}
            {m.questions.filter((q) => q.classification === "optional").length} optional
          </p>
          <h2 className="mt-1 font-serif text-2xl">{m.title}</h2>
          <p className="mt-1 text-sm text-ink-muted">{m.description}</p>
        </button>
        <div className="flex shrink-0 items-center gap-1">
          <button onClick={() => onMove(-1)} disabled={saving || index === 0} className="rounded-full p-2 text-ink-muted hover:bg-cream disabled:opacity-30" aria-label="Move up"><ArrowUp className="h-4 w-4" /></button>
          <button onClick={() => onMove(1)} disabled={saving || index === count - 1} className="rounded-full p-2 text-ink-muted hover:bg-cream disabled:opacity-30" aria-label="Move down"><ArrowDown className="h-4 w-4" /></button>
          <button onClick={onDelete} disabled={saving} className="rounded-full p-2 text-ink-muted hover:bg-amber/10 hover:text-amber disabled:opacity-30" aria-label="Remove module"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
      {open && (
        <div className="space-y-6 border-t border-line bg-paper/60 p-6">
          <div className="grid gap-4 sm:grid-cols-[1fr_1fr]">
            <Field label="Title" value={m.title} rows={1} onSave={(title) => onSave({ title })} />
            <label className="block">
              <span className="eyebrow !text-[10px]">Suggested session</span>
              <select value={m.session_group} onChange={(e) => onSave({ session_group: Number(e.target.value) })} className="mt-1.5 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-gold/60">
                {[1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>Session {n}</option>)}
              </select>
            </label>
          </div>
          <Field label="Family (e.g. Ikigai, Purpose)" value={m.description} rows={1} onSave={(description) => onSave({ description })} />
          <Field label="Introduction shown when the module begins" value={m.intro} onSave={(intro) => onSave({ intro })} />
          <div className="flex flex-wrap items-center gap-6">
            <Toggle label={m.active ? "Active: clients see this module" : "Inactive: hidden from clients"} value={m.active} onChange={(active) => onSave({ active })} />
            <label className="inline-flex items-center gap-2 text-xs text-ink-soft">
              Follow-ups
              <select value={m.follow_up_mode} onChange={(e) => onSave({ follow_up_mode: e.target.value as "pool" | "compose" })} className="rounded-lg border border-line bg-paper px-2 py-1 text-xs outline-none">
                <option value="pool">from this module&apos;s follow-up questions only</option>
                <option value="compose">the AI may compose its own</option>
              </select>
            </label>
          </div>

          <div className="space-y-4 border-t border-line pt-6">
            {m.questions.map((q, qi) => (
              <div key={q.id}>
              {q.section && (qi === 0 || m.questions[qi - 1].section !== q.section) && (
                <p className="mb-3 mt-2 border-b border-line pb-1 font-serif text-lg text-ink">{q.section}</p>
              )}
              <div className={`rounded-2xl border border-line bg-white p-5 ${q.active ? "" : "opacity-60"}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className="flex items-center gap-2">
                    <span className="font-serif text-sm text-gold">{String(qi + 1).padStart(2, "0")}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${CLASS_BADGE[q.classification]}`}>{q.classification.replace("_", "-")}</span>
                    {q.flags && q.flags.length > 0 && <span className="rounded-full bg-amber/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-amber">Review</span>}
                  </span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => onMoveQuestion(qi, -1)} disabled={saving || qi === 0} className="rounded-full p-1.5 text-ink-muted hover:bg-cream disabled:opacity-30" aria-label="Move up"><ArrowUp className="h-3.5 w-3.5" /></button>
                    <button onClick={() => onMoveQuestion(qi, 1)} disabled={saving || qi === m.questions.length - 1} className="rounded-full p-1.5 text-ink-muted hover:bg-cream disabled:opacity-30" aria-label="Move down"><ArrowDown className="h-3.5 w-3.5" /></button>
                    <button onClick={() => onDeleteQuestion(q)} disabled={saving} className="rounded-full p-1.5 text-ink-muted hover:bg-amber/10 hover:text-amber disabled:opacity-30" aria-label="Remove question"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
                <div className="mt-2 space-y-4">
                  {q.flags && q.flags.length > 0 && (
                    <ul className="space-y-1 rounded-xl border border-amber/30 bg-amber/5 px-3 py-2 text-xs text-ink-soft">
                      {q.flags.map((f) => <li key={f}>{f}</li>)}
                    </ul>
                  )}
                  <Field label="Section heading" value={q.section} rows={1} onSave={(section) => onSaveQuestion(q.id, { section })} />
                  <Field label="Question (shown to the client)" value={q.prompt} mono onSave={(prompt) => onSaveQuestion(q.id, { prompt })} />
                  <Field label="Follow-up guidance (what the AI listens for; never shown to the client)" value={q.follow_up_guidance} onSave={(follow_up_guidance) => onSaveQuestion(q.id, { follow_up_guidance })} />
                  <div className="flex flex-wrap items-center gap-6">
                    <label className="inline-flex items-center gap-2 text-xs text-ink-soft">
                      Use as
                      <select value={q.classification} onChange={(e) => onSaveQuestion(q.id, { classification: e.target.value as Classification })} className="rounded-lg border border-line bg-paper px-2 py-1 text-xs outline-none">
                        {(Object.keys(CLASS_LABEL) as Classification[]).map((c) => <option key={c} value={c}>{CLASS_LABEL[c]}</option>)}
                      </select>
                    </label>
                    <Toggle label={q.required ? "Required (skip asks for confirmation)" : "May be skipped freely"} value={q.required} onChange={(required) => onSaveQuestion(q.id, { required })} />
                    <label className="inline-flex items-center gap-2 text-xs text-ink-soft">
                      Follow-ups
                      <select value={q.max_follow_ups} onChange={(e) => onSaveQuestion(q.id, { max_follow_ups: Number(e.target.value) })} className="rounded-lg border border-line bg-paper px-2 py-1 text-xs outline-none">
                        {[0, 1, 2].map((n) => <option key={n} value={n}>{n === 0 ? "none" : `up to ${n}`}</option>)}
                      </select>
                    </label>
                    {q.answer_count ? <span className="text-xs text-ink-muted/70">{q.answer_count} answer{q.answer_count === 1 ? "" : "s"} recorded</span> : null}
                  </div>
                </div>
              </div>
              </div>
            ))}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (newPrompt.trim()) {
                  onAddQuestion(newPrompt.trim());
                  setNewPrompt("");
                }
              }}
              className="flex items-end gap-2"
            >
              <label className="block flex-1">
                <span className="eyebrow !text-[10px]">Add a question</span>
                <input value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)} placeholder="Type the question as the client will read it…" className="mt-1.5 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-gold/60" />
              </label>
              <button disabled={saving || !newPrompt.trim()} className="btn-primary !px-4 !py-2">
                <Plus className="h-4 w-4" /> Add
              </button>
            </form>
          </div>
        </div>
      )}
    </FadeIn>
  );
}

function AddModule({ onAdd, saving }: { onAdd: (title: string) => void; saving: boolean }) {
  const [title, setTitle] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (title.trim()) {
          onAdd(title.trim());
          setTitle("");
        }
      }}
      className="card flex items-end gap-2 p-6"
    >
      <label className="block flex-1">
        <span className="eyebrow !text-[10px]">Add a module</span>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Health" className="mt-1.5 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-gold/60" />
      </label>
      <button disabled={saving || !title.trim()} className="btn-primary !px-4 !py-2">
        <Plus className="h-4 w-4" /> Add module
      </button>
    </form>
  );
}
