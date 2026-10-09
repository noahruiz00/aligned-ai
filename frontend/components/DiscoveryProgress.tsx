"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { Step } from "@/lib/api";

/** Ten-step discovery tracker with a progress bar. Used by the client flow and, later, the advisor view. */
export function DiscoveryProgress({ steps, pct, compact = false }: { steps: Step[]; pct: number; compact?: boolean }) {
  const current = steps.find((s) => s.status === "in_progress");
  const lastDone = [...steps].reverse().find((s) => s.status === "completed");
  return (
    <div className="border-b border-line/70 bg-paper">
      <div className={`mx-auto max-w-5xl px-5 sm:px-8 ${compact ? "py-3" : "py-4"}`}>
        <div className="flex items-baseline justify-between gap-4">
          <p className="eyebrow">
            Discovery <span className="ml-2 font-serif text-base normal-case tracking-normal text-ink">{pct}%</span>
          </p>
          <p className="truncate text-xs text-ink-muted">
            {lastDone && <span className="hidden sm:inline">{lastDone.title} completed · </span>}
            {current && (
              <span className="text-ink-soft">
                {current.title} {current.kind === "module" ? "in progress" : ""}
              </span>
            )}
          </p>
        </div>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-cream">
          <motion.div className="h-full bg-gradient-to-r from-gold-light to-gold-deep" animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }} />
        </div>
        {!compact && (
          <ol className="mt-4 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
            {steps.map((s) => (
              <li
                key={s.key}
                className={`flex shrink-0 items-center gap-2 rounded-full border px-3 py-1 text-xs transition ${
                  s.status === "in_progress"
                    ? "border-gold bg-gold-pale/40 text-ink"
                    : s.status === "completed"
                      ? "border-line bg-white text-ink-muted"
                      : "border-transparent text-ink-muted/50"
                }`}
              >
                {s.status === "completed" ? (
                  <Check className="h-3 w-3 text-gold-deep" strokeWidth={2.5} />
                ) : (
                  <span className="font-serif">{String(s.index).padStart(2, "0")}</span>
                )}
                {s.title}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
