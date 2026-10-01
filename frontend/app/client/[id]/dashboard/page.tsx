"use client";

import Link from "next/link";
import { ArrowRight, Briefcase, FileText, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { CategoryCards, ScoreSummary } from "@/components/ScoreBreakdown";
import { FadeIn, Spinner, TopBar, ValueIcon } from "@/components/ui";
import { api, type Dashboard } from "@/lib/api";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function ClientDashboard({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  const firstName = data?.user.name.split(/[ &]/)[0];

  return (
    <main className="min-h-screen pb-24">
      <TopBar
        right={
          <>
            <Link href={`/client/${id}/statement`} className="btn-ghost !px-4 !py-2">
              <FileText className="h-4 w-4" /> <span className="hidden sm:inline">My statement</span>
            </Link>
            <Link href={`/advisor/${id}`} className="btn-ghost !px-4 !py-2">
              <Briefcase className="h-4 w-4" /> <span className="hidden sm:inline">Advisor view</span>
            </Link>
          </>
        }
      />
      {error && <p className="p-10 text-center text-amber">{error}</p>}
      {!data && !error && <Spinner label="Preparing your dashboard…" />}
      {data && !data.score && (
        <div className="p-16 text-center">
          <p className="text-ink-muted">Your alignment hasn&apos;t been measured yet.</p>
          <Link href={`/client/${id}/portrait`} className="btn-primary mt-6">
            Measure my alignment <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
      {data?.score && (
        <div className="mx-auto max-w-6xl px-5 pt-12 sm:px-8">
          <FadeIn>
            <p className="eyebrow">
              {greeting()}, {firstName}
            </p>
            {data.purpose && (
              <h1 className="mt-5 max-w-4xl font-serif text-3xl leading-snug italic text-ink-soft sm:text-[2.6rem] sm:leading-[1.25]">
                “{data.purpose.purpose_statement}”
              </h1>
            )}
            {data.values && (
              <div className="mt-8 flex flex-wrap gap-2">
                {data.values.values.map((v) => (
                  <span key={v.name} className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-sm text-ink-soft">
                    <span className="text-gold-deep">
                      <ValueIcon name={v.name} className="h-4 w-4" />
                    </span>
                    {v.name}
                  </span>
                ))}
              </div>
            )}
          </FadeIn>

          <FadeIn delay={0.15} className="mt-12">
            <ScoreSummary score={data.score} />
          </FadeIn>

          <div className="mt-16">
            <p className="eyebrow">Where you stand</p>
            <h2 className="mt-3 font-serif text-4xl">Alignment, area by area</h2>
            <div className="mt-8">
              <CategoryCards score={data.score} audience="client" />
            </div>
          </div>

          <div className="mt-16 grid gap-5 md:grid-cols-2">
            <div className="card p-8">
              <p className="eyebrow">Next step</p>
              <h3 className="mt-3 font-serif text-2xl">Your advisor has been shared this view</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                At your next meeting, you&apos;ll walk through these areas together and decide on one alignment action
                for the next ninety days.
              </p>
            </div>
            <div className="card p-8">
              <p className="eyebrow">Stewardship</p>
              <h3 className="mt-3 font-serif text-2xl">Life changes. Your score should too.</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">Update your financial portrait whenever something meaningful shifts.</p>
              <Link href={`/client/${id}/portrait`} className="mt-5 inline-flex items-center gap-2 text-sm text-gold-deep hover:underline">
                <RefreshCw className="h-3.5 w-3.5" /> Update my portrait
              </Link>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
