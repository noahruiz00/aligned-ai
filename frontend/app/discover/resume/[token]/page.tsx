"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Spinner, TopBar } from "@/components/ui";
import { api } from "@/lib/api";

/** Private resume link: exchanges the token for the session cookie, then continues the discovery. The token never
 *  appears anywhere but this URL, and the page replaces itself in history so it is not left in the address bar. */
export default function ResumePage({ params }: { params: { token: string } }) {
  const router = useRouter();
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    api.resumeDiscovery(params.token)
      .then((s) => router.replace(s.session.status === "complete" ? `/client/${s.session.user_id}/statement` : "/discover"))
      .catch(() => setInvalid(true));
  }, [params.token, router]);

  return (
    <main className="min-h-screen">
      <TopBar />
      {!invalid ? (
        <Spinner label="Opening your discovery…" />
      ) : (
        <div className="mx-auto max-w-md px-5 py-24 text-center sm:px-8">
          <h1 className="font-serif text-3xl">That link isn&apos;t valid.</h1>
          <p className="mt-4 text-sm leading-relaxed text-ink-muted">
            It may have been copied incompletely. Check the link you were given, or begin a new discovery.
          </p>
          <Link href="/discover" className="btn-primary mt-8">Begin a discovery</Link>
        </div>
      )}
    </main>
  );
}
