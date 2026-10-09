"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Pencil, PauseCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, KeyboardEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { ClientReview } from "@/components/ClientReview";
import { DiscoveryProgress } from "@/components/DiscoveryProgress";
import { FadeIn, Logo, Spinner, TopBar } from "@/components/ui";
import { api, type DiscoveryState, type Exchange, type Household, type Turn } from "@/lib/api";

export default function DiscoverPage() {
  return (
    <Suspense fallback={<main className="min-h-screen"><TopBar /><Spinner label="Opening…" /></main>}>
      <Discover />
    </Suspense>
  );
}

type View = "intake" | "question" | "module_done" | "review" | "paused" | "generating";

function Discover() {
  const router = useRouter();
  const [state, setState] = useState<DiscoveryState | null>(null);
  const [view, setView] = useState<View>("intake");
  const [lastTurn, setLastTurn] = useState<Turn | null>(null);
  const [resume, setResume] = useState<DiscoveryState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const s = await api.discovery();
    setState(s);
    if (s.session.status === "complete") router.replace(`/client/${s.session.user_id}/statement`);
    else setView(s.current ? "question" : "review");
    return s;
  }, [router]);

  // This device's session, if any, is identified by its HttpOnly cookie. Resume links go through /discover/resume/{token}.
  useEffect(() => {
    api.discovery().then((s) => (s.session.status === "complete" ? undefined : setResume(s))).catch(() => undefined);
  }, []);

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  function apply(s: DiscoveryState) {
    setState(s);
    setView(s.current ? "question" : "review");
  }

  async function start(name: string, household: Household) {
    const s = await run(() => api.startDiscovery(name, household));
    if (!s) return;
    apply(s);
  }

  async function submitAnswer(text: string) {
    if (!state?.current) return;
    const { question, pending_follow_up } = state.current;
    const r = await run(() => api.answer({ question_id: question.id, text, parent_answer_id: pending_follow_up?.parent_answer_id, input_mode: "text" }));
    if (!r) return;
    setLastTurn(r.turn);
    setState(r.state);
    setView(r.turn.module_completed ? "module_done" : r.state.current ? "question" : "review");
  }

  async function skip(reason: "skip" | "prefer_not" = "skip") {
    if (!state?.current) return;
    const { question, pending_follow_up } = state.current;
    const r = await run(() => api.skip({ question_id: question.id, parent_answer_id: pending_follow_up?.parent_answer_id, reason }));
    if (!r) return;
    setLastTurn(r.turn);
    setState(r.state);
    setView(r.turn.module_completed ? "module_done" : r.state.current ? "question" : "review");
  }

  const back = async () => state && apply((await run(() => api.back())) ?? state);
  const next = async () => state && apply((await run(() => api.next())) ?? state);
  const goto = async (qid: number) => state && apply((await run(() => api.goto(qid))) ?? state);
  async function share(sharing: "shared_with_advisor" | "private") {
    if (!state) return;
    const s = await run(() => api.share(sharing));
    if (s) setState(s);
  }

  async function deeper(moduleKey: string) {
    if (!state) return;
    const s = await run(() => api.deeper(moduleKey));
    if (s) apply(s);
  }

  async function pause() {
    if (!state) return;
    const s = await run(() => api.pause());
    if (s) {
      setState(s);
      setView("paused");
    }
  }

  async function feedback(moduleKey: string, kind: "yes" | "partly" | "edit", correction?: string) {
    if (!state) return;
    const s = await run(() => api.reflectionFeedback(moduleKey, kind, correction));
    if (s) setState(s);
  }

  async function complete() {
    if (!state) return;
    setView("generating");
    const r = await run(() => api.completeDiscovery());
    if (!r) {
      setView("review");
      return;
    }
    router.push(`/client/${r.user_id}/statement`);
  }

  if (view === "generating") {
    return (
      <main className="min-h-screen">
        <TopBar />
        <Spinner label="Drafting your Wealth Purpose Statement from what you confirmed…" />
      </main>
    );
  }

  if (!state || view === "intake") {
    return <Intake onStart={start} busy={busy} error={error} resume={resume} onResume={() => load().catch(() => setResume(null))} onDiscard={() => { if (confirm("Start fresh? Your unfinished answers will be set aside and your old link will stop working.")) api.forgetDiscovery().finally(() => setResume(null)); }} />;
  }

  const demoBadge = state.demo_mode && <span className="rounded-full bg-cream px-3 py-1 text-xs text-ink-muted">Demo mode</span>;

  if (view === "paused") {
    const link = typeof window !== "undefined" ? `${window.location.origin}/discover/resume/${state.session.resume_token}` : "";
    return (
      <main className="min-h-screen">
        <TopBar right={demoBadge} />
        <DiscoveryProgress steps={state.steps} pct={state.progress_pct} compact />
        <div className="mx-auto max-w-xl px-5 py-20 text-center sm:px-8">
          <FadeIn>
            <PauseCircle className="mx-auto h-8 w-8 text-gold" strokeWidth={1.4} />
            <h1 className="mt-6 font-serif text-4xl">Your progress is saved.</h1>
            <p className="mt-4 leading-relaxed text-ink-muted">
              Come back whenever you have a quiet moment. On this device, just return to this page. Elsewhere, use your private link:
            </p>
            <code className="mt-5 block select-all break-all rounded-xl border border-line bg-white px-4 py-3 text-xs text-ink-soft">{link}</code>
            <p className="mt-3 rounded-xl border border-amber/40 bg-amber/5 px-4 py-3 text-sm text-ink-soft">
              Anyone with this private resume link can access your session. Do not share it.
            </p>
            <button onClick={() => setView(state.current ? "question" : "review")} className="btn-primary mt-10">
              Keep going <ArrowRight className="h-4 w-4" />
            </button>
          </FadeIn>
        </div>
      </main>
    );
  }

  const pauseButton = (
    <button onClick={pause} disabled={busy} className="btn-ghost !px-4 !py-2">
      <PauseCircle className="h-4 w-4" /> <span className="hidden sm:inline">Save &amp; continue later</span>
    </button>
  );

  if (view === "module_done" && lastTurn?.module_completed) {
    const key = lastTurn.module_completed;
    return (
      <main className="min-h-screen">
        <TopBar right={<>{demoBadge}{pauseButton}</>} />
        <DiscoveryProgress steps={state.steps} pct={state.progress_pct} />
        <ModuleDone
          state={state}
          moduleKey={key}
          turn={lastTurn}
          busy={busy}
          onFeedback={(k, c) => feedback(key, k, c)}
          onContinue={() => setView(state.current ? "question" : "review")}
          onDeeper={() => deeper(key)}
          onPause={pause}
        />
        {error && <p className="mt-4 text-center text-sm text-amber">{error}</p>}
      </main>
    );
  }

  if (view === "review" || !state.current) {
    return (
      <main className="min-h-screen pb-24">
        <TopBar right={<>{demoBadge}{pauseButton}</>} />
        <DiscoveryProgress steps={state.steps} pct={state.progress_pct} />
        <ClientReview state={state} busy={busy} error={error} onEdit={goto} onComplete={complete} onShare={share} />
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-16">
      <TopBar right={<>{demoBadge}{pauseButton}</>} />
      <DiscoveryProgress steps={state.steps} pct={state.progress_pct} />
      <Question
        key={`${state.current.question.id}-${state.current.pending_follow_up?.parent_answer_id ?? "q"}`}
        state={state}
        lastTurn={lastTurn}
        busy={busy}
        error={error}
        onAnswer={submitAnswer}
        onSkip={() => skip("skip")}
        onDecline={() => skip("prefer_not")}
        onPause={pause}
        onBack={back}
        onNext={next}
        onClarify={goto}
      />
    </main>
  );
}

// --- Intake -------------------------------------------------------------------

function Intake({ onStart, busy, error, resume, onResume, onDiscard }: {
  onStart: (name: string, household: Household) => void;
  busy: boolean;
  error: string | null;
  resume: DiscoveryState | null;
  onResume: () => void;
  onDiscard: () => void;
}) {
  const [name, setName] = useState("");
  const [household, setHousehold] = useState<Household>("individual");
  function submit(e: FormEvent) {
    e.preventDefault();
    if (name.trim()) onStart(name.trim(), household);
  }
  return (
    <main className="min-h-screen">
      <TopBar />
      <div className="mx-auto max-w-xl px-5 py-20 sm:px-8">
        {resume && (
          <FadeIn className="card mb-10 border-gold/40 bg-gold-pale/20 p-6">
            <p className="eyebrow">Welcome back, {resume.session.name.split(/[ &]/)[0]}</p>
            <p className="mt-2 text-sm text-ink-muted">Your discovery is {resume.progress_pct}% complete. Pick up where you left off?</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button onClick={onResume} className="btn-primary !py-2.5">
                Continue <ArrowRight className="h-4 w-4" />
              </button>
              <button onClick={onDiscard} className="btn-ghost !py-2.5">Start fresh</button>
            </div>
          </FadeIn>
        )}
        <FadeIn>
          <p className="eyebrow">Discover</p>
          <h1 className="mt-4 font-serif text-5xl leading-tight">
            Let&apos;s begin with <em className="text-gold-deep">you</em>, not your portfolio.
          </h1>
          <p className="mt-6 leading-relaxed text-ink-muted">
            A private, unhurried conversation in short sections: purpose, love, play, work, service, alignment, community, and how you&apos;ve
            evolved. One question at a time. Pause whenever you like; your progress is saved.
          </p>
        </FadeIn>
        <FadeIn delay={0.15}>
          <form onSubmit={submit} className="card mt-10 space-y-8 p-8">
            <label className="block">
              <span className="eyebrow">Your name</span>
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Sarah Johnson"
                className="mt-3 w-full border-b border-line bg-transparent pb-2 font-serif text-2xl outline-none transition placeholder:text-ink-muted/40 focus:border-gold"
              />
            </label>
            <div>
              <span className="eyebrow">I&apos;m planning as</span>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {(["individual", "couple", "family"] as Household[]).map((h) => (
                  <button
                    type="button"
                    key={h}
                    onClick={() => setHousehold(h)}
                    className={`rounded-xl border px-3 py-3 text-sm transition ${household === h ? "border-gold bg-gold-pale/40 text-ink" : "border-line text-ink-muted hover:border-gold/50"}`}
                  >
                    {h === "individual" ? "An individual" : h === "couple" ? "A couple" : "A family"}
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" disabled={!name.trim() || busy} className="btn-primary w-full">
              {busy ? "Preparing…" : "Begin"} <ArrowRight className="h-4 w-4" />
            </button>
            {error && <p className="text-sm text-amber">{error}</p>}
          </form>
        </FadeIn>
        <p className="mt-6 text-center text-[11px] text-ink-muted/70">
          Nothing is shared with your advisor until you choose to share it. This is not financial advice.
        </p>
      </div>
    </main>
  );
}

// --- Question view ------------------------------------------------------------

function ExchangeRow({ e, onClarify, disabled }: { e: Exchange; onClarify: (qid: number) => void; disabled: boolean }) {
  return (
    <div className="space-y-3 border-l border-line pl-5">
      <p className="font-serif text-lg italic text-ink-muted">{e.prompt}</p>
      {e.answer.skipped ? (
        <p className="text-sm text-ink-muted/70">{e.answer.declined ? "Preferred not to answer" : "Skipped"}</p>
      ) : (
        <p className="whitespace-pre-wrap leading-relaxed text-ink-soft">{e.answer.text}</p>
      )}
      {e.answer.reflection && !e.answer.skipped && <Reflection text={e.answer.reflection} small />}
      {e.follow_up && (
        <div className="space-y-2 pl-4">
          <p className="font-serif text-base italic text-ink-muted">{e.follow_up.prompt}</p>
          {e.follow_up.answer && (e.follow_up.answer.skipped ? <p className="text-sm text-ink-muted/70">{e.follow_up.answer.declined ? "Preferred not to answer" : "Skipped"}</p> : <p className="whitespace-pre-wrap leading-relaxed text-ink-soft">{e.follow_up.answer.text}</p>)}
          {e.follow_up.answer?.reflection && !e.follow_up.answer.skipped && <Reflection text={e.follow_up.answer.reflection} small />}
        </div>
      )}
      <button onClick={() => onClarify(e.question_id)} disabled={disabled} className="inline-flex items-center gap-1.5 text-xs text-gold-deep hover:underline disabled:opacity-40">
        <Pencil className="h-3 w-3" /> Clarify this answer
      </button>
    </div>
  );
}

/** Exchanges in order, with the methodology's section heading shown whenever it changes. */
function ExchangeList({ exchanges, onClarify, disabled }: { exchanges: Exchange[]; onClarify: (qid: number) => void; disabled: boolean }) {
  return (
    <div className="space-y-8">
      {exchanges.map((e, i) => (
        <div key={e.question_id} className="space-y-4">
          {e.section && (i === 0 || exchanges[i - 1].section !== e.section) && <p className="text-sm text-gold-deep">{e.section}</p>}
          <ExchangeRow e={e} onClarify={onClarify} disabled={disabled} />
        </div>
      ))}
    </div>
  );
}

function Reflection({ text, small = false }: { text: string; small?: boolean }) {
  return (
    <div className="flex gap-3">
      <span className={`mt-1 shrink-0 text-gold ${small ? "scale-90" : ""}`}>
        <Logo className={small ? "h-4 w-4" : "h-5 w-5"} />
      </span>
      <p className={`font-serif italic leading-relaxed text-ink-soft ${small ? "text-base" : "text-xl"}`}>{text}</p>
    </div>
  );
}

function Question({ state, lastTurn, busy, error, onAnswer, onSkip, onDecline, onPause, onBack, onNext, onClarify }: {
  state: DiscoveryState;
  lastTurn: Turn | null;
  busy: boolean;
  error: string | null;
  onAnswer: (text: string) => void;
  onSkip: () => void;
  onDecline: () => void;
  onPause: () => void;
  onBack: () => void;
  onNext: () => void;
  onClarify: (qid: number) => void;
}) {
  const cur = state.current!;
  const editing = cur.existing_answer !== null;
  const [text, setText] = useState(editing && !cur.existing_answer?.skipped ? cur.existing_answer!.text : "");
  const ref = useRef<HTMLTextAreaElement>(null);
  const prompt = cur.pending_follow_up?.prompt ?? cur.question.prompt;
  const showIntro = cur.exchanges.length === 0 && !cur.pending_follow_up && !editing;
  // The reflection on the answer just given is shown above the follow-up question.
  const freshReflection = cur.pending_follow_up && lastTurn?.follow_up === cur.pending_follow_up.prompt ? lastTurn?.reflection : null;

  useEffect(() => {
    ref.current?.focus();
  }, []);

  function submit() {
    const t = text.trim();
    if (!t || busy) return;
    onAnswer(t);
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 pt-10 sm:px-8">
      <FadeIn>
        <p className="eyebrow">
          Session {cur.module.session_group} · Step {cur.module.index} · {cur.module.title}
          <span className="ml-3 normal-case tracking-normal text-ink-muted/70">
            {cur.question.classification === "optional" ? "Going deeper · " : ""}
            {cur.question.position} of {cur.question.total}
          </span>
        </p>
        {showIntro && cur.module.intro && <p className="mt-4 max-w-xl leading-relaxed text-ink-muted">{cur.module.intro}</p>}
      </FadeIn>

      {cur.exchanges.length > 0 && (
        <div className="mt-8">
          <ExchangeList exchanges={cur.exchanges} onClarify={onClarify} disabled={busy} />
        </div>
      )}

      <AnimatePresence mode="wait">
        <motion.div key={prompt} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} className="mt-10">
          {freshReflection && (
            <div className="mb-6">
              <Reflection text={freshReflection} />
            </div>
          )}
          {editing && (
            <p className="mb-3 text-xs text-ink-muted">
              {cur.existing_answer?.declined ? "You chose not to answer this earlier. That still stands unless you type something." : cur.existing_answer?.skipped ? "You skipped this one earlier." : "You answered this earlier. Update it, or continue without changes."}
            </p>
          )}
          {cur.question.section && !cur.pending_follow_up && <p className="mb-3 text-sm text-gold-deep">{cur.question.section}</p>}
          <h1 className="font-serif text-3xl leading-snug text-ink sm:text-[2.4rem] sm:leading-[1.2]">
            {cur.pending_follow_up && <span className="mr-2 text-gold">↳</span>}
            {prompt}
          </h1>
          {!cur.question.required && !cur.pending_follow_up && <p className="mt-2 text-xs text-ink-muted/70">Optional</p>}
        </motion.div>
      </AnimatePresence>

      <div className="mt-8">
        <div className="rounded-2xl border border-line bg-white p-2 pl-5 shadow-card focus-within:border-gold/60">
          <textarea
            ref={ref}
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            disabled={busy}
            placeholder="Take your time. A sentence or two is plenty…"
            className="w-full resize-none bg-transparent py-2.5 leading-relaxed outline-none placeholder:text-ink-muted/50 disabled:opacity-60"
          />
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line/70 px-1 pt-2">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
              <button onClick={onBack} disabled={busy || (cur.is_first && !cur.pending_follow_up)} className="inline-flex items-center gap-1 hover:text-ink disabled:opacity-30">
                <ArrowLeft className="h-3.5 w-3.5" /> Back
              </button>
              <button onClick={onSkip} disabled={busy} className="hover:text-ink disabled:opacity-30">
                Skip {cur.pending_follow_up ? "follow-up" : "for now"}
              </button>
              <button onClick={onDecline} disabled={busy} className="hover:text-ink disabled:opacity-30">
                Prefer not to answer
              </button>
              <button onClick={onPause} disabled={busy} className="inline-flex items-center gap-1 hover:text-ink disabled:opacity-30">
                <PauseCircle className="h-3.5 w-3.5" /> Pause session
              </button>
              {editing && (
                <button onClick={onNext} disabled={busy} className="hover:text-ink disabled:opacity-30">
                  Continue without changes
                </button>
              )}
            </div>
            <button onClick={submit} disabled={!text.trim() || busy} className="btn-primary !px-5 !py-2">
              {busy ? "Listening…" : editing ? "Update" : "Continue"} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-amber">{error}</p>}
        <p className="mt-3 text-center text-[11px] text-ink-muted/70">
          Press Enter to continue, Shift+Enter for a new line. Nothing here is required: skip, decline, or pause at any point. Your progress saves automatically.
        </p>
      </div>
    </div>
  );
}

// --- Module complete ----------------------------------------------------------

function ModuleDone({ state, moduleKey, turn, busy, onFeedback, onContinue, onDeeper, onPause }: {
  state: DiscoveryState;
  moduleKey: string;
  turn: Turn;
  busy: boolean;
  onFeedback: (kind: "yes" | "partly" | "edit", correction?: string) => Promise<void>;
  onContinue: () => void;
  onDeeper: () => void;
  onPause: () => void;
}) {
  const refl = state.module_reflections[moduleKey];
  const title = state.steps.find((s) => s.key === moduleKey)?.title ?? moduleKey;
  const [mode, setMode] = useState<"ask" | "correct" | "done">(refl?.feedback ? "done" : "ask");
  const [kind, setKind] = useState<"partly" | "edit">("partly");
  const [correction, setCorrection] = useState("");

  async function choose(k: "yes" | "partly" | "edit") {
    if (k === "yes") {
      await onFeedback("yes");
      setMode("done");
    } else {
      setKind(k);
      setMode("correct");
    }
  }

  async function sendCorrection() {
    await onFeedback(kind, correction.trim() || undefined);
    setMode("done");
  }

  return (
    <div className="mx-auto max-w-2xl px-5 pt-12 sm:px-8">
      <FadeIn>
        <p className="eyebrow">{title} · complete</p>
        <h1 className="mt-4 font-serif text-4xl">What we&apos;re hearing</h1>
      </FadeIn>
      {refl && (
        <FadeIn delay={0.1} className="card mt-8 p-8">
          <p className="font-serif text-xl leading-relaxed text-ink-soft">{refl.summary}</p>
          {refl.themes.length > 0 && (
            <div className="mt-8 space-y-5 border-t border-line pt-6">
              {refl.themes.map((t) => (
                <div key={t.name}>
                  <p className="font-medium text-ink">{t.name}</p>
                  <p className="mt-1 text-sm leading-relaxed text-ink-muted">{t.note}</p>
                </div>
              ))}
            </div>
          )}
          <div className="mt-8 border-t border-line pt-6">
            {mode === "ask" && (
              <>
                <p className="text-sm text-ink-soft">Does this feel accurate?</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => choose("yes")} disabled={busy} className="btn-primary !py-2">
                    <Check className="h-4 w-4" /> Yes
                  </button>
                  <button onClick={() => choose("partly")} disabled={busy} className="btn-ghost !py-2">Partly</button>
                  <button onClick={() => choose("edit")} disabled={busy} className="btn-ghost !py-2">
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </button>
                </div>
              </>
            )}
            {mode === "correct" && (
              <>
                <p className="text-sm text-ink-soft">{kind === "edit" ? "What should this say instead?" : "What would you change or add?"}</p>
                <textarea
                  autoFocus
                  value={correction}
                  onChange={(e) => setCorrection(e.target.value)}
                  rows={3}
                  className="mt-3 w-full resize-none rounded-xl border border-line bg-paper p-3 text-sm outline-none focus:border-gold/60"
                  placeholder="In your own words…"
                />
                <div className="mt-3 flex gap-2">
                  <button onClick={sendCorrection} disabled={busy || (kind === "edit" && !correction.trim())} className="btn-primary !py-2">Save</button>
                  <button onClick={() => setMode("ask")} className="btn-ghost !py-2">Cancel</button>
                </div>
              </>
            )}
            {mode === "done" && (
              <p className="flex items-center gap-2 text-sm text-sage">
                <Check className="h-4 w-4" /> {refl.feedback === "yes" ? "Thank you. We'll build on this." : "Noted. Your words take precedence over ours."}
              </p>
            )}
          </div>
        </FadeIn>
      )}
      <FadeIn delay={0.2} className="mt-8">
        {turn.suggest_pause && turn.next_module && (
          <p className="mb-4 text-sm text-ink-muted">
            This is a natural place to pause before <span className="text-ink">{turn.next_module.title}</span>. Your progress is saved either way.
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <button onClick={onContinue} disabled={busy} className="btn-primary">
            {turn.next_module ? `Continue to ${turn.next_module.title}` : "Review what you shared"} <ArrowRight className="h-4 w-4" />
          </button>
          {turn.optional_available > 0 && (
            <button onClick={onDeeper} disabled={busy} className="btn-ghost">
              Go deeper into {title} ({turn.optional_available} more question{turn.optional_available === 1 ? "" : "s"})
            </button>
          )}
          {turn.suggest_pause && (
            <button onClick={onPause} disabled={busy} className="btn-ghost">
              <PauseCircle className="h-4 w-4" /> Pause here
            </button>
          )}
        </div>
      </FadeIn>
    </div>
  );
}
