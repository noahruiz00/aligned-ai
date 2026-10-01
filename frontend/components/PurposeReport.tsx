"use client";

import { FadeIn, Logo, ValueIcon } from "@/components/ui";
import type { Purpose, ValuesProfile } from "@/lib/api";

const GUIDE_LABELS: [keyof Purpose["guides"], string][] = [
  ["investments", "Investments"],
  ["estate", "Trust & Estate"],
  ["philanthropy", "Philanthropic Giving"],
  ["cash_flow", "Cash Flow"],
];

export function PurposeReport({ name, purpose, values, date }: { name: string; purpose: Purpose; values?: ValuesProfile | null; date?: string | null }) {
  const dated = date ? new Date(date).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;
  return (
    <article className="mx-auto max-w-4xl">
      {/* Cover */}
      <FadeIn className="relative overflow-hidden rounded-3xl bg-ink px-8 py-16 text-center text-paper sm:px-16 sm:py-20 print:rounded-none">
        <div className="mx-auto w-fit text-gold-light">
          <Logo className="h-10 w-10" />
        </div>
        <p className="eyebrow mt-8 !text-gold-light">Wealth Purpose Statement</p>
        <p className="mt-2 text-sm text-paper/50">
          Prepared for {name}
          {dated && ` · ${dated}`}
        </p>
        <blockquote className="mx-auto mt-10 max-w-2xl font-serif text-3xl leading-snug italic sm:text-[2.6rem] sm:leading-[1.2]">
          “{purpose.purpose_statement}”
        </blockquote>
      </FadeIn>

      {/* Core values */}
      <section className="mt-16">
        <p className="eyebrow">Core values</p>
        <div className="rule mt-3" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {purpose.core_values.map((v, i) => (
            <FadeIn key={v.name} delay={0.1 + i * 0.08} className="card flex gap-5 p-6">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gold-pale/50 text-gold-deep">
                <ValueIcon name={v.name} />
              </div>
              <div>
                <h3 className="font-serif text-2xl">{v.name}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-muted">{v.meaning}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* Vision & philosophy */}
      <section className="mt-16 grid gap-10 md:grid-cols-2">
        <div>
          <p className="eyebrow">Meaningful life vision</p>
          <div className="rule mt-3" />
          <p className="mt-6 font-serif text-xl leading-relaxed text-ink-soft">{purpose.meaningful_life_vision.summary}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            {purpose.meaningful_life_vision.pillars.map((p) => (
              <span key={p} className="rounded-full border border-gold/40 px-4 py-1.5 text-sm text-gold-deep">
                {p}
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className="eyebrow">Wealth philosophy</p>
          <div className="rule mt-3" />
          <p className="mt-6 font-serif text-xl leading-relaxed text-ink-soft">{purpose.wealth_philosophy}</p>
        </div>
      </section>

      {/* Legacy */}
      <section className="mt-16 rounded-3xl border border-line bg-cream/70 px-8 py-12 text-center sm:px-16">
        <p className="eyebrow">Legacy</p>
        <p className="mx-auto mt-5 max-w-2xl font-serif text-2xl leading-relaxed italic text-ink-soft sm:text-3xl">
          {purpose.legacy_statement}
        </p>
      </section>

      {/* Downstream */}
      <section className="print-break mt-16">
        <p className="eyebrow">Why it matters downstream</p>
        <div className="rule mt-3" />
        <p className="mt-6 max-w-2xl text-ink-muted">
          This statement will inform investments, trust &amp; estate, philanthropic giving, and cash flow management, so
          that your values and the purpose of your wealth stay in alignment with your financial life.
        </p>
        <div className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2">
          {GUIDE_LABELS.map(([k, label]) => (
            <div key={k} className="bg-white p-7">
              <h4 className="font-serif text-xl">{label}</h4>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{purpose.guides[k]}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Accountability */}
      <section className="mt-16">
        <p className="eyebrow">Accountability measures</p>
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

      {values?.money_script && (
        <section className="mt-16 border-l-2 border-gold/50 pl-6">
          <p className="eyebrow">Your money story</p>
          <p className="mt-3 font-serif text-xl italic leading-relaxed text-ink-soft">{values.money_script}</p>
        </section>
      )}

      <p className="mt-16 text-center text-xs text-ink-muted">
        A living document. Revisit it together with your advisor at least once a year.
      </p>
    </article>
  );
}
