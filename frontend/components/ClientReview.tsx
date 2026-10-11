"use client";

import { ArrowRight, Check, ChevronDown, HelpCircle, Pencil } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { FadeIn, Spinner } from "@/components/ui";
import { api, type DiscoveryState, type Insight, type InsightFeedbackKind, type InsightType } from "@/lib/api";

/** Review sections in the order the client sees them, and the insight types each one draws from. */
export const REVIEW_SECTIONS: { title: string; types: InsightType[]; blurb: string }[] = [
  { title: "Your Emerging Wealth Purpose", types: ["wealth_purpose"], blurb: "What you said your wealth is for." },
  { title: "Personal Values", types: ["personal_values"], blurb: "Values that kept appearing." },
  { title: "Financial Values", types: ["financial_values"], blurb: "What you want money to fund first." },
  { title: "Meaningful Life Themes", types: ["meaningful_life_themes", "work_themes"], blurb: "What a good life looks like to you." },
  { title: "Goals", types: ["goals"], blurb: "Things you said you want to do or have." },
  { title: "Money's Role", types: ["money_role", "money_beliefs", "emotional_themes"], blurb: "The part money plays, and how it feels." },
  { title: "Money Story", types: ["money_story"], blurb: "Where your relationship with money began." },
  { title: "Family / Legacy", types: ["family_context", "legacy_themes"], blurb: "The people, and what should outlast you." },
  { title: "Community / Philanthropy", types: ["community_priorities", "philanthropic_interests", "service_themes"], blurb: "Who and what you want to help." },
  { title: "Open Questions", types: ["tensions", "open_questions", "uncertainties", "declined_topic"], blurb: "Where we'd rather ask than guess, and what you chose to leave aside." },
];

const STATUS_LABEL: Record<Insight["status"], { label: string; cls: string }> = {
  ai_detected: { label: "AI detected", cls: "bg-cream text-ink-muted" },
  needs_clarification: { label: "Needs clarification", cls: "bg-amber/10 text-amber" },
  client_confirmed: { label: "Confirmed by you", cls: "bg-sage/10 text-sage" },
  client_corrected: { label: "Corrected by you", cls: "bg-gold-pale/60 text-gold-deep" },
  advisor_confirmed: { label: "Confirmed by your advisor", cls: "bg-sage/10 text-sage" },
};

const BASIS_LABEL: Record<Insight["basis"], string> = {
  client_fact: "Something you stated",
  client_statement: "In your words",
  ai_interpretation: "Our reading",
};

export function ClientReview({ state, busy, error, onEdit, onComplete, onShare }: {
  state: DiscoveryState;
  busy: boolean;
  error: string | null;
  onEdit: (qid: number) => void;
  onComplete: () => void;
  onShare: (sharing: "shared_with_advisor" | "private") => Promise<void>;
}) {
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(() => api.insights().then((r) => setInsights(r.insights)).catch((e) => setLoadError(e.message)), []);
  useEffect(() => {
    load();
  }, [load]);

  async function feedback(id: number, kind: InsightFeedbackKind, text?: string) {
    const updated = await api.insightFeedback(id, kind, text);
    setInsights((list) => (list ? list.map((i) => (i.id === id ? updated : i)) : list));
  }

  const confirmed = insights?.filter((i) => i.status === "client_confirmed" || i.status === "client_corrected").length ?? 0;
  const isOpenType = (t: InsightType) => t === "open_questions" || t === "uncertainties" || t === "declined_topic";
  const reviewable = insights?.filter((i) => !isOpenType(i.type) && i.primary).length ?? 0;
  const secondary = insights?.filter((i) => !i.primary).length ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-5 pt-12 sm:px-8">
      <FadeIn>
        <p className="eyebrow">Session {state.steps[state.steps.length - 1].session_group} · Review</p>
        <h1 className="mt-4 font-serif text-4xl leading-tight">Here&apos;s what Aligned AI understood about you.</h1>
        <p className="mt-4 max-w-xl leading-relaxed text-ink-muted">
          Every line below comes from something you said. Tell us where we got it right, where we only got it partly, and what to change.
          Nothing is treated as fact until you confirm it.
        </p>
      </FadeIn>

      {loadError && <p className="mt-8 text-sm text-amber">{loadError}</p>}
      {!insights && !loadError && <Spinner label="Gathering what we heard…" />}

      {insights && (
        <>
          <div className="mt-8 flex flex-wrap items-center gap-3 text-xs text-ink-muted">
            <span className="rounded-full border border-line px-3 py-1">{reviewable} insights{secondary > 0 ? ` · ${secondary} more available` : ""}</span>
            <span className="rounded-full border border-line px-3 py-1">{confirmed} confirmed or corrected</span>
            <span className="rounded-full border border-line px-3 py-1">{insights.filter((i) => i.status === "needs_clarification").length} need clarification</span>
          </div>

          <div className="mt-10 space-y-12">
            {REVIEW_SECTIONS.map((sec, si) => (
              <ReviewSection key={sec.title} sec={sec} index={si} insights={insights.filter((i) => sec.types.includes(i.type))} state={state} busy={busy} onFeedback={feedback} onEdit={onEdit} />
            ))}
          </div>
        </>
      )}

      <ShareCard sharing={state.session.sharing} busy={busy} onShare={onShare} />

      <div className="card mt-6 flex flex-col items-start justify-between gap-6 p-8 sm:flex-row sm:items-center">
        <div>
          <p className="eyebrow">Next · Wealth Purpose</p>
          <h3 className="mt-2 font-serif text-2xl">Ready to draft your statement?</h3>
          <p className="mt-2 text-sm text-ink-muted">
            A first draft, built from what you confirmed or corrected above. Anything still marked “needs clarification” is left out rather than guessed.
          </p>
          {!state.can_complete && <p className="mt-2 text-sm text-amber">A few core questions still need an answer (or a skip).</p>}
        </div>
        <button onClick={onComplete} disabled={busy || !state.can_complete} className="btn-primary shrink-0">
          Create my draft statement <ArrowRight className="h-4 w-4" />
        </button>
      </div>
      {error && <p className="mt-4 text-sm text-amber">{error}</p>}
    </div>
  );
}

/** One review section: the strongest insights first; the rest fold away so the page stays readable. */
function ReviewSection({ sec, index, insights, state, busy, onFeedback, onEdit }: {
  sec: (typeof REVIEW_SECTIONS)[number];
  index: number;
  insights: Insight[];
  state: DiscoveryState;
  busy: boolean;
  onFeedback: (id: number, kind: InsightFeedbackKind, text?: string) => Promise<void>;
  onEdit: (qid: number) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const primary = insights.filter((i) => i.primary);
  const rest = insights.filter((i) => !i.primary);
  const items = showAll ? insights : primary;
  return (
    <FadeIn delay={0.04 * index}>
      <p className="eyebrow">{sec.title}</p>
      <div className="rule mt-2" />
      <p className="mt-2 text-xs text-ink-muted">{sec.blurb}</p>
      <div className="mt-5 space-y-4">
        {insights.length === 0 && (
          <p className="rounded-2xl border border-dashed border-line px-5 py-4 text-sm text-ink-muted">
            Needs clarification — nothing in your answers supported this yet. You can go back and add to an answer.
          </p>
        )}
        {items.map((i) => (
          <InsightCard key={i.id} insight={i} state={state} busy={busy} onFeedback={onFeedback} onEdit={onEdit} />
        ))}
        {rest.length > 0 && (
          <button onClick={() => setShowAll((v) => !v)} className="text-xs text-gold-deep hover:underline">
            {showAll ? "Show fewer" : `Show ${rest.length} more`}
          </button>
        )}
      </div>
    </FadeIn>
  );
}

/** Explicit consent. Nothing reaches the advisor until the client chooses to share, and they can withdraw it. */
function ShareCard({ sharing, busy, onShare }: { sharing: DiscoveryState["session"]["sharing"]; busy: boolean; onShare: (s: "shared_with_advisor" | "private") => Promise<void> }) {
  const shared = sharing === "shared_with_advisor" || sharing === "pending_share";
  return (
    <div className={`card mt-14 p-8 ${shared ? "border-sage/40" : "border-gold/40 bg-gold-pale/10"}`}>
      <p className="eyebrow">Sharing with your advisor</p>
      {shared ? (
        <>
          <h3 className="mt-2 font-serif text-2xl">
            {sharing === "pending_share" ? "Your profile will be shared once your statement is drafted." : "Your profile is shared with your advisor."}
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">
            Your advisor can see your Wealth Purpose Statement, the insights you confirmed or corrected, your open questions, and the words behind
            them. You can withdraw this at any time.
          </p>
          <button onClick={() => onShare("private")} disabled={busy} className="btn-ghost mt-4 !py-2">Stop sharing</button>
        </>
      ) : (
        <>
          <h3 className="mt-2 font-serif text-2xl">Share my Wealth Purpose Profile with my advisor</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">
            Right now, nothing here is visible to anyone but you. If you share, your advisor receives: your Wealth Purpose Statement draft; the
            values, goals, meaningful-life themes, money story, family and community themes you confirmed or corrected; your open questions;
            and the quoted answers each one rests on. They do <strong>not</strong> receive answers you skipped or declined, or anything you
            haven&apos;t reviewed.
          </p>
          <button onClick={() => onShare("shared_with_advisor")} disabled={busy} className="btn-primary mt-4 !py-2">
            <Check className="h-4 w-4" /> Share my profile
          </button>
        </>
      )}
    </div>
  );
}

function InsightCard({ insight: i, state, busy, onFeedback, onEdit }: {
  insight: Insight;
  state: DiscoveryState;
  busy: boolean;
  onFeedback: (id: number, kind: InsightFeedbackKind, text?: string) => Promise<void>;
  onEdit: (qid: number) => void;
}) {
  const [why, setWhy] = useState(false);
  const [mode, setMode] = useState<null | "partly" | "edit" | "clarify">(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const st = STATUS_LABEL[i.status];
  const isOpen = i.type === "open_questions" || i.type === "uncertainties" || i.type === "declined_topic";
  const prompts = new Map<number, string>();
  for (const m of state.modules) for (const e of m.exchanges) {
    prompts.set(e.question_id, e.prompt);
    if (e.follow_up?.question_id) prompts.set(e.follow_up.question_id, e.follow_up.prompt);
  }

  async function send(kind: InsightFeedbackKind) {
    setSaving(true);
    try {
      await onFeedback(i.id, kind, text.trim() || undefined);
      setMode(null);
      setText("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={`card p-5 ${i.status === "needs_clarification" ? "border-amber/30" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-ink">{i.label}</h3>
            {i.type === "tensions" && <span className="rounded-full bg-amber/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-amber">Tension</span>}
            {i.type === "declined_topic" && <span className="rounded-full bg-cream px-2 py-0.5 text-[10px] uppercase tracking-wide text-ink-muted">Left aside</span>}
            <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${st.cls}`}>{st.label}</span>
            <span className="text-[10px] uppercase tracking-wide text-ink-muted/70">{BASIS_LABEL[i.basis]}</span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-ink-soft">{i.summary}</p>
          {i.client_correction && (
            <p className="mt-2 border-l-2 border-gold pl-3 text-sm leading-relaxed text-ink">
              <span className="eyebrow !text-[9px]">{i.client_feedback === "clarify" ? "Your clarification" : "Your words"}</span>
              <br />
              {i.client_correction}
            </p>
          )}
        </div>
        <button onClick={() => setWhy((w) => !w)} className="inline-flex shrink-0 items-center gap-1 text-xs text-gold-deep hover:underline">
          <HelpCircle className="h-3.5 w-3.5" /> Why? <ChevronDown className={`h-3 w-3 transition ${why ? "rotate-180" : ""}`} />
        </button>
      </div>

      {why && (
        <div className="mt-4 space-y-3 rounded-xl bg-cream/60 p-4">
          <p className="eyebrow !text-[9px]">
            {i.evidence.length ? "Based on what you said" : "No direct quote — this is a gap we noticed, not a claim"}
            {!isOpen && ` · confidence ${Math.round(i.confidence * 100)}%`}
          </p>
          {i.evidence.map((e) => (
            <div key={e.id} className="text-sm">
              <p className="text-xs leading-snug text-ink-muted">
                {e.module}{e.section ? ` › ${e.section}` : ""}
                {prompts.get(e.question_id) && <span className="italic"> — “{prompts.get(e.question_id)}”</span>}
              </p>
              <p className="mt-1 font-serif text-base italic leading-relaxed text-ink-soft">“{e.excerpt}”</p>
              <button onClick={() => onEdit(e.question_id)} disabled={busy} className="mt-1 inline-flex items-center gap-1 text-xs text-gold-deep hover:underline disabled:opacity-40">
                <Pencil className="h-3 w-3" /> Clarify this answer
              </button>
            </div>
          ))}
        </div>
      )}

      {!isOpen && mode === null && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => send("accurate")} disabled={busy || saving} className="btn-primary !px-4 !py-1.5 !text-xs">
            <Check className="h-3.5 w-3.5" /> Accurate
          </button>
          <button onClick={() => setMode("partly")} disabled={busy || saving} className="btn-ghost !px-4 !py-1.5 !text-xs">Partly</button>
          <button onClick={() => setMode("edit")} disabled={busy || saving} className="btn-ghost !px-4 !py-1.5 !text-xs">Edit</button>
          <button onClick={() => setMode("clarify")} disabled={busy || saving} className="btn-ghost !px-4 !py-1.5 !text-xs">Clarify</button>
        </div>
      )}
      {isOpen && mode === null && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => setMode("clarify")} disabled={busy || saving} className="btn-ghost !px-4 !py-1.5 !text-xs">Answer this</button>
        </div>
      )}
      {mode !== null && (
        <div className="mt-4">
          <p className="text-xs text-ink-muted">
            {mode === "partly" ? "What's not quite right?" : mode === "edit" ? "What should this say instead?" : "Add a few words of clarification."}
          </p>
          <textarea autoFocus value={text} onChange={(e) => setText(e.target.value)} rows={3} className="mt-2 w-full resize-none rounded-xl border border-line bg-paper p-3 text-sm outline-none focus:border-gold/60" placeholder="In your own words…" />
          <div className="mt-2 flex gap-2">
            <button onClick={() => send(mode)} disabled={saving || !text.trim()} className="btn-primary !px-4 !py-1.5 !text-xs">Save</button>
            <button onClick={() => { setMode(null); setText(""); }} className="btn-ghost !px-4 !py-1.5 !text-xs">Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
