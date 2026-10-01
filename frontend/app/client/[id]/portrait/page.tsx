"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { FadeIn, Spinner, TopBar } from "@/components/ui";
import { api, type Portrait } from "@/lib/api";

const DEFAULTS: Portrait = {
  spending_on_priorities_pct: 55,
  has_spending_plan: false,
  values_aligned_allocation_pct: 15,
  portfolio_values_review: "no",
  has_will: true,
  has_trust: false,
  has_legacy_letter: false,
  family_conversations: "occasional",
  annual_giving_pct: 2,
  giving_alignment: "somewhat",
  has_giving_vehicle: false,
  emergency_reserve_months: 6,
  insurance_reviewed_recently: false,
  concentrated_position: false,
};

function Section({ n, title, question, children }: { n: string; title: string; question: string; children: ReactNode }) {
  return (
    <section className="card grid gap-8 p-8 md:grid-cols-[220px_1fr]">
      <div>
        <span className="font-serif text-sm text-gold">{n}</span>
        <h2 className="mt-1 font-serif text-2xl">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">{question}</p>
      </div>
      <div className="space-y-7">{children}</div>
    </section>
  );
}

function Slider({ label, value, onChange, min = 0, max = 100, step = 1, suffix = "%" }: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number; suffix?: string }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm text-ink-soft">{label}</span>
        <span className="font-serif text-2xl text-gold-deep">
          {value}
          <span className="text-base">{suffix}</span>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-3 w-full accent-[#A9824A]"
      />
    </label>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" onClick={() => onChange(!value)} className="flex w-full items-center justify-between gap-4 text-left">
      <span className="text-sm text-ink-soft">{label}</span>
      <span className={`relative h-6 w-11 shrink-0 rounded-full transition ${value ? "bg-gold" : "bg-line"}`}>
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${value ? "left-[22px]" : "left-0.5"}`} />
      </span>
    </button>
  );
}

function Choice<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div>
      <span className="text-sm text-ink-soft">{label}</span>
      <div className="mt-3 grid gap-2" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
        {options.map(([v, text]) => (
          <button
            type="button"
            key={v}
            onClick={() => onChange(v)}
            className={`rounded-xl border px-3 py-2.5 text-sm transition ${value === v ? "border-gold bg-gold-pale/40" : "border-line text-ink-muted hover:border-gold/50"}`}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function PortraitPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const router = useRouter();
  const [p, setP] = useState<Portrait>(DEFAULTS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof Portrait>(k: K) => (v: Portrait[K]) => setP((prev) => ({ ...prev, [k]: v }));

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.calculateScore(id, p);
      router.push(`/client/${id}/dashboard`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  if (busy) {
    return (
      <main className="min-h-screen">
        <TopBar />
        <Spinner label="Measuring your alignment…" />
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-24">
      <TopBar />
      <div className="mx-auto max-w-4xl px-5 pt-14 sm:px-8">
        <FadeIn>
          <p className="eyebrow">Steward · Your financial portrait</p>
          <h1 className="mt-4 font-serif text-5xl leading-tight">
            Is your wealth <em className="text-gold-deep">supporting</em> your vision?
          </h1>
          <p className="mt-5 max-w-2xl leading-relaxed text-ink-muted">
            Approximate answers are perfect. Your advisor will refine the picture with you. Nothing here is linked to
            your accounts.
          </p>
        </FadeIn>

        <FadeIn delay={0.15} className="mt-12 space-y-5">
          <Section n="01" title="Cash Flow" question="Are spending habits aligned with your values?">
            <Slider label="Share of discretionary spending that goes to what you named as meaningful" value={p.spending_on_priorities_pct} onChange={set("spending_on_priorities_pct")} />
            <Toggle label="I have a written spending plan" value={p.has_spending_plan} onChange={set("has_spending_plan")} />
          </Section>

          <Section n="02" title="Investment" question="Does your portfolio reflect your purpose?">
            <Slider label="Share of the portfolio intentionally aligned with your values (ESG, impact, mission-related)" value={p.values_aligned_allocation_pct} onChange={set("values_aligned_allocation_pct")} />
            <Choice label="Has your portfolio been reviewed against your values?" value={p.portfolio_values_review} onChange={set("portfolio_values_review")} options={[["yes", "Yes"], ["partly", "Partly"], ["no", "Not yet"]]} />
          </Section>

          <Section n="03" title="Estate & Legacy" question="Does your plan transfer values, not only assets?">
            <div className="grid gap-5 sm:grid-cols-3">
              <Toggle label="Will" value={p.has_will} onChange={set("has_will")} />
              <Toggle label="Trust" value={p.has_trust} onChange={set("has_trust")} />
              <Toggle label="Legacy letter" value={p.has_legacy_letter} onChange={set("has_legacy_letter")} />
            </div>
            <Choice label="How often does your family talk about the purpose of its wealth?" value={p.family_conversations} onChange={set("family_conversations")} options={[["regular", "Regularly"], ["occasional", "Occasionally"], ["never", "Rarely"]]} />
          </Section>

          <Section n="04" title="Philanthropy" question="Is your giving aligned with the causes you care about?">
            <Slider label="Annual giving as a share of income" value={p.annual_giving_pct} onChange={set("annual_giving_pct")} max={20} step={0.5} />
            <Choice label="How is your giving directed?" value={p.giving_alignment} onChange={set("giving_alignment")} options={[["intentional", "Intentionally"], ["somewhat", "Somewhat"], ["ad_hoc", "Ad hoc"]]} />
            <Toggle label="I use a giving vehicle (donor-advised fund, foundation)" value={p.has_giving_vehicle} onChange={set("has_giving_vehicle")} />
          </Section>

          <Section n="05" title="Risk Management" question="Is your vision protected against what could derail it?">
            <Slider label="Months of expenses held in reserve" value={p.emergency_reserve_months} onChange={set("emergency_reserve_months")} max={24} suffix=" mo" />
            <Toggle label="Insurance reviewed in the last two years" value={p.insurance_reviewed_recently} onChange={set("insurance_reviewed_recently")} />
            <Toggle label="More than 25% of wealth in a single holding or business" value={p.concentrated_position} onChange={set("concentrated_position")} />
          </Section>
        </FadeIn>

        <div className="mt-10 flex items-center justify-end gap-4">
          {error && <p className="text-sm text-amber">{error}</p>}
          <button onClick={submit} className="btn-primary">
            Calculate my Wealth Alignment Score <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </main>
  );
}
