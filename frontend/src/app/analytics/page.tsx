import { fetchAnalyticsOverview } from "@/lib/api";
import { BarChart } from "@/components/BarChart";
import { FramingBar } from "@/components/FramingBar";
import { FRAMING_LABELS, FRAMING_TEXT } from "@/lib/framing";
import type { FramingCounts } from "@/lib/api";

export default async function AnalyticsPage() {
  let data: Awaited<ReturnType<typeof fetchAnalyticsOverview>> | null = null;
  let error = false;
  try {
    data = await fetchAnalyticsOverview();
  } catch {
    error = true;
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.16em] text-foreground/50">Desk</p>
        <h1 className="font-serif text-3xl font-semibold">Analytics</h1>
        <p className="max-w-2xl text-sm text-foreground/65">
          Live aggregates from <code className="text-xs">/api/analytics/overview</code>.
        </p>
      </header>

      {error || !data ? (
        <p className="text-sm text-accent">Unable to load analytics overview.</p>
      ) : (
        <>
          <div className="grid gap-px border border-foreground/15 bg-foreground/15 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Active sources", data.sources_active],
              ["Total sources", data.sources_total],
              ["Claim statuses", Object.keys(data.claims_by_status).length],
              ["Last crawl", data.last_crawl?.status ?? "—"],
            ].map(([label, value]) => (
              <div key={String(label)} className="bg-surface px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-foreground/45">{label}</p>
                <p className="mt-1 font-serif text-2xl tabular-nums">{value}</p>
              </div>
            ))}
          </div>

          {data.last_crawl && (
            <p className="text-xs text-foreground/55">
              Last crawl #{data.last_crawl.id}: started{" "}
              {data.last_crawl.started_at
                ? new Date(data.last_crawl.started_at).toLocaleString()
                : "—"}
              , {data.last_crawl.articles_new ?? 0} new articles,{" "}
              {data.last_crawl.feeds_failed ?? 0} feed failures.
            </p>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="border border-border bg-surface p-5">
              <h2 className="font-serif text-lg font-semibold">Articles by language</h2>
              <div className="mt-4">
                <BarChart data={data.articles_by_language} />
              </div>
            </section>
            <section className="border border-border bg-surface p-5">
              <h2 className="font-serif text-lg font-semibold">Articles by topic tag</h2>
              <div className="mt-4">
                <BarChart data={data.articles_by_topic} maxItems={15} />
              </div>
            </section>
          </div>

          <section className="border border-border bg-surface p-5">
            <h2 className="font-serif text-lg font-semibold">Government framing</h2>
            <FramingBar counts={data.framing as FramingCounts} className="mt-4" height="h-5" />
            <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
              {(Object.keys(FRAMING_LABELS) as (keyof FramingCounts)[]).map((key) => (
                <li key={key} className={FRAMING_TEXT[key]}>
                  {FRAMING_LABELS[key]}:{" "}
                  <span className="font-semibold text-foreground">{data!.framing[key] ?? 0}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="border border-border bg-surface p-5">
            <h2 className="font-serif text-lg font-semibold">Claims by status</h2>
            <div className="mt-4">
              <BarChart data={data.claims_by_status} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
