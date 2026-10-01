"use client";

import Link from "next/link";
import { ArrowRight, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { PurposeReport } from "@/components/PurposeReport";
import { Spinner, TopBar } from "@/components/ui";
import { api, type Dashboard } from "@/lib/api";

export default function StatementPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  const actions = data && (
    <>
      <button onClick={() => window.print()} className="btn-ghost !px-4 !py-2">
        <Download className="h-4 w-4" /> <span className="hidden sm:inline">Download PDF</span>
      </button>
      <Link href={data.score ? `/client/${id}/dashboard` : `/client/${id}/portrait`} className="btn-primary !px-4 !py-2">
        {data.score ? "View alignment" : "Continue"} <ArrowRight className="h-4 w-4" />
      </Link>
    </>
  );

  return (
    <main className="min-h-screen pb-24">
      <TopBar right={actions} />
      {error && <p className="p-10 text-center text-amber">{error}</p>}
      {!data && !error && <Spinner label="Opening your statement…" />}
      {data && !data.purpose && <p className="p-10 text-center text-ink-muted">No statement yet. Complete the discovery conversation first.</p>}
      {data?.purpose && (
        <div className="px-5 pt-10 sm:px-8">
          <PurposeReport name={data.user.name} purpose={data.purpose} values={data.values} date={data.purpose_created_at} />
          {!data.score && (
            <div className="no-print mx-auto mt-16 max-w-4xl">
              <div className="card flex flex-col items-start justify-between gap-6 p-8 sm:flex-row sm:items-center">
                <div>
                  <p className="eyebrow">Next · Steward</p>
                  <h3 className="mt-2 font-serif text-3xl">Is your wealth supporting this vision?</h3>
                  <p className="mt-2 text-sm text-ink-muted">A few quick questions about your financial life produce your Wealth Alignment Score.</p>
                </div>
                <Link href={`/client/${id}/portrait`} className="btn-primary shrink-0">
                  Measure my alignment <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
