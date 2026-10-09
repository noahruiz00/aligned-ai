"use client";

import { FadeIn, Logo } from "@/components/ui";
import type { Purpose, PurposeSections } from "@/lib/api";

const ORDER: (keyof PurposeSections)[] = [
  "vision", "money_role", "purpose_of_wealth", "personal_values", "financial_values", "meaningful_life", "family_legacy", "community_philanthropy", "money_story",
];

/** The sectioned Wealth Purpose Statement draft generated from discovery insights. */
export function DraftStatement({ name, sections, purpose, date }: { name: string; sections: PurposeSections; purpose: Purpose; date?: string | null }) {
  const dated = date ? new Date(date).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;
  return (
    <article className="mx-auto max-w-4xl">
      <div className="no-print mb-6 flex items-center justify-center gap-3 rounded-full border border-amber/40 bg-amber/5 px-5 py-2 text-xs uppercase tracking-eyebrow text-amber">
        Draft — generated from your discovery
      </div>
      <FadeIn className="relative overflow-hidden rounded-3xl bg-ink px-8 py-16 text-center text-paper sm:px-16 sm:py-20 print:rounded-none">
        <div className="mx-auto w-fit text-gold-light">
          <Logo className="h-10 w-10" />
        </div>
        <p className="eyebrow mt-8 !text-gold-light">Wealth Purpose Statement · Draft</p>
        <p className="mt-2 text-sm text-paper/50">
          Prepared for {name}
          {dated && ` · ${dated}`}
        </p>
        <blockquote className="mx-auto mt-10 max-w-2xl font-serif text-2xl leading-snug italic sm:text-[2.2rem] sm:leading-[1.25]">
          “{sections.purpose_of_wealth.text}”
        </blockquote>
      </FadeIn>

      <div className="mt-14 space-y-12">
        {ORDER.map((key, i) => {
          const s = sections[key];
          const unclear = s.text.startsWith("Needs clarification");
          return (
            <FadeIn key={key} delay={0.05 * i}>
              <p className="eyebrow">{s.title}</p>
              <div className="rule mt-3" />
              <p className={`mt-6 font-serif text-xl leading-relaxed ${unclear ? "italic text-amber" : "text-ink-soft"}`}>{s.text}</p>
              {s.insight_ids.length > 0 && (
                <p className="mt-2 text-[11px] text-ink-muted/70">Drawn from {s.insight_ids.length} confirmed or high-confidence insight{s.insight_ids.length === 1 ? "" : "s"}.</p>
              )}
            </FadeIn>
          );
        })}
      </div>

      {purpose.accountability_measures.length > 0 && (
        <section className="mt-16">
          <p className="eyebrow">Questions to ask yourself each year</p>
          <div className="rule mt-3" />
          <ol className="mt-6 space-y-4">
            {purpose.accountability_measures.map((m, i) => (
              <li key={i} className="flex gap-5">
                <span className="font-serif text-2xl text-gold">{i + 1}</span>
                <span className="pt-1.5 leading-relaxed text-ink-soft">{m}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <p className="mt-16 text-center text-xs text-ink-muted">
        A draft, not a conclusion. It contains no financial, investment, tax or legal advice. Refine it with your advisor.
      </p>
    </article>
  );
}
