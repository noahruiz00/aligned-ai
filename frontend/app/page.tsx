"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Briefcase } from "lucide-react";
import { FadeIn, Logo } from "@/components/ui";

const QUESTIONS = [
  { lead: "What is the", key: "purpose", tail: "of your wealth?" },
  { lead: "What does a", key: "meaningful life", tail: "look like to you?" },
  { lead: "Is your wealth", key: "supporting", tail: "that vision today?" },
];

const METHOD = [
  { n: "01", t: "Discover", d: "A guided conversation about the purpose of your wealth and the life you want it to serve." },
  { n: "02", t: "Harvest", d: "Your values, emotional cues, and family money story are drawn out and made explicit." },
  { n: "03", t: "Architect", d: "A Wealth Purpose Statement: a living document that anchors every decision that follows." },
  { n: "04", t: "Steward", d: "A Wealth Alignment Score shows where your financial life reflects your purpose, and where it doesn't yet." },
];

export default function Landing() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden bg-ink text-paper">
        <div className="pointer-events-none absolute inset-0 opacity-[0.07]" style={{ backgroundImage: "radial-gradient(circle at 50% 0%, #C9A873 0, transparent 60%)" }} />
        <nav className="relative mx-auto flex h-20 max-w-6xl items-center justify-between px-5 sm:px-8">
          <div className="flex items-center gap-2.5 text-gold-light">
            <Logo />
            <span className="font-serif text-xl tracking-wide text-paper">
              Aligned <span className="text-gold-light">AI</span>
            </span>
          </div>
          <Link href="/advisor" className="flex items-center gap-2 text-sm text-paper/70 transition hover:text-gold-light">
            <Briefcase className="h-4 w-4" strokeWidth={1.5} /> Advisor view
          </Link>
        </nav>

        <div className="relative mx-auto max-w-4xl px-5 pb-28 pt-16 text-center sm:px-8 sm:pt-24">
          <FadeIn>
            <motion.div
              className="mx-auto mb-10 w-fit text-gold-light"
              initial={{ rotate: -45, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
            >
              <Logo className="h-14 w-14" />
            </motion.div>
            <p className="eyebrow !text-gold-light">Wealth Purpose Companion</p>
          </FadeIn>
          <FadeIn delay={0.15}>
            <h1 className="mt-6 font-serif text-5xl leading-[1.05] sm:text-7xl">
              Wealth as a tool for <br className="hidden sm:block" />
              <em className="text-gold-light">living a meaningful life.</em>
            </h1>
          </FadeIn>
          <FadeIn delay={0.3}>
            <p className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-paper/70">
              Before portfolios and structures, there is a simpler question. A short, private conversation
              to discover what your wealth is truly for.
            </p>
          </FadeIn>
          <FadeIn delay={0.45} className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/discover" className="inline-flex items-center gap-2 rounded-full bg-gold-light px-8 py-4 text-sm font-medium text-ink transition hover:bg-paper">
              Begin your discovery <ArrowRight className="h-4 w-4" />
            </Link>
            <span className="text-sm text-paper/50">About ten minutes · Completely private</span>
          </FadeIn>
        </div>
      </section>

      {/* Three questions */}
      <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8">
        <p className="eyebrow text-center">The foundation</p>
        <h2 className="mx-auto mt-4 max-w-2xl text-center font-serif text-4xl leading-tight sm:text-5xl">
          Three simple questions that govern the rest of the financial plan.
        </h2>
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {QUESTIONS.map((q, i) => (
            <FadeIn key={q.key} delay={i * 0.12} className="card p-8">
              <span className="font-serif text-sm text-gold">{`0${i + 1}`}</span>
              <p className="mt-6 font-serif text-2xl leading-snug italic text-ink-soft">
                {q.lead} <span className="text-gold-deep">{q.key}</span> {q.tail}
              </p>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* Method */}
      <section className="border-y border-line bg-cream/60">
        <div className="mx-auto grid max-w-6xl gap-16 px-5 py-24 sm:px-8 lg:grid-cols-[1fr_1.4fr]">
          <div>
            <p className="eyebrow">The method</p>
            <h2 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
              From who you are, <br />
              <em className="text-gold-deep">to how your wealth behaves.</em>
            </h2>
            <p className="mt-6 max-w-md leading-relaxed text-ink-muted">
              Blending Ikigai, Dharma, and your financial portrait, the process treats emotional cues as
              information about what you value, and serves individuals, couples, and families alike.
            </p>
          </div>
          <div className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2">
            {METHOD.map((m) => (
              <div key={m.n} className="bg-paper p-8">
                <span className="font-serif text-sm text-gold">{m.n}</span>
                <h3 className="mt-3 font-serif text-2xl italic">{m.t}</h3>
                <p className="mt-3 text-sm leading-relaxed text-ink-muted">{m.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Closing */}
      <section className="mx-auto max-w-3xl px-5 py-28 text-center sm:px-8">
        <p className="font-serif text-3xl leading-snug italic text-ink-soft sm:text-4xl">
          “A meaningful life comes first, and wealth exists to support that vision — not the other way around.”
        </p>
        <Link href="/discover" className="btn-primary mt-12">
          Begin your discovery <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <footer className="border-t border-line py-10 text-center text-xs text-ink-muted">
        Aligned AI supports your advisor&apos;s judgement. It does not provide investment, tax, or legal advice.
      </footer>
    </main>
  );
}
