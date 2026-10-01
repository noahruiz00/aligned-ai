"use client";

import { motion } from "framer-motion";
import { Bar, FadeIn, ScoreRing, scoreTone } from "@/components/ui";
import type { CategoryKey, Score } from "@/lib/api";

export const CATEGORY_ORDER: CategoryKey[] = ["cash_flow", "investment", "estate", "philanthropy", "risk"];

export function ScoreSummary({ score, compact = false }: { score: Score; compact?: boolean }) {
  const tone = scoreTone(score.overall);
  return (
    <div className={`card grid gap-10 p-8 ${compact ? "" : "sm:p-10"} md:grid-cols-[auto_1fr] md:items-center`}>
      <div className="flex flex-col items-center gap-4">
        <ScoreRing value={score.overall} size={compact ? 150 : 190} label="Overall" />
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${tone.cls}`}>{tone.label}</span>
      </div>
      <div>
        <p className="eyebrow">Wealth Alignment Score</p>
        <div className="mt-6 space-y-5">
          {CATEGORY_ORDER.map((k, i) => {
            const c = score.categories[k];
            return (
              <div key={k}>
                <div className="mb-2 flex items-baseline justify-between">
                  <span className="text-sm text-ink-soft">{c.label}</span>
                  <span className="font-serif text-xl">{c.score}%</span>
                </div>
                <Bar value={c.score} delay={0.3 + i * 0.1} />
              </div>
            );
          })}
        </div>
        {!compact && (
          <p className="mt-6 text-xs leading-relaxed text-ink-muted">
            Weighted by your values. {score.weighting_rationale.join(" ")}
          </p>
        )}
      </div>
    </div>
  );
}

export function CategoryCards({ score, audience }: { score: Score; audience: "client" | "advisor" }) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {CATEGORY_ORDER.map((k, i) => {
        const c = score.categories[k];
        const tone = scoreTone(c.score);
        return (
          <FadeIn key={k} delay={0.1 + i * 0.06} className={`card p-7 ${i === CATEGORY_ORDER.length - 1 ? "md:col-span-2" : ""}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-serif text-2xl">{c.label}</h3>
                <p className="mt-1 text-sm italic text-ink-muted">{c.question}</p>
              </div>
              <div className="text-right">
                <motion.span className="font-serif text-4xl" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  {c.score}
                  <span className="text-lg text-gold">%</span>
                </motion.span>
                <p className={`mt-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] ${tone.cls}`}>{tone.label}</p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-relaxed text-ink-soft">{c.explanation}</p>
            <div className="mt-5 border-t border-line pt-5">
              <p className="eyebrow !text-[10px]">{audience === "client" ? "To explore with your advisor" : "Suggested focus"}</p>
              <ul className="mt-3 space-y-2">
                {c.recommendations.map((r) => (
                  <li key={r} className="flex gap-3 text-sm leading-relaxed text-ink-muted">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </FadeIn>
        );
      })}
    </div>
  );
}
