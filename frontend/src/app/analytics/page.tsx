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
        <h1 className="font-serif text-3xl font-bold">Analytics</h1>
        <p className="max-w-2xl text-sm text-foreground/60">
          Live aggregates from <code className="text-xs">/api/analytics/overview</code> — no
          synthetic metrics.
        </p>
      </header>

      {error || !data ? (
        <p className="card p-6 text-sm text-red-700">Unable to load analytics overview.</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Active sources", data.sources_active],
              ["Total sources", data.sources_total],
              ["Claim statuses", Object.keys(data.claims_by_status).length],
              [
                "Last crawl",
                data.last_crawl?.status ?? "—",
              ],
            ].map(([label, value]) => (
              <div key={String(label)} className="card p-4">
                <p className="text-xs font-bold uppercase text-foreground/45">{label}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
              </div>
            ))}
          </div>

          {data.last_crawl && (
            <p className="text-xs text-foreground/50">
              Last crawl #{data.last_crawl.id}: started{" "}
              {data.last_crawl.started_at
                ? new Date(data.last_crawl.started_at).toLocaleString()
                : "—"}
              , {data.last_crawl.articles_new ?? 0} new articles,{" "}
              {data.last_crawl.feeds_failed ?? 0} feed failures.
            </p>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="card p-5">
              <h2 className="font-serif text-lg font-bold">Articles by language</h2>
              <div className="mt-4">
                <BarChart data={data.articles_by_language} />
              </div>
            </section>
            <section className="card p-5">
              <h2 className="font-serif text-lg font-bold">Articles by topic tag</h2>
              <div className="mt-4">
                <BarChart data={data.articles_by_topic} maxItems={15} />
              </div>
            </section>
          </div>

          <section className="card p-5">
            <h2 className="font-serif text-lg font-bold">Government framing (corpus)</h2>
            <FramingBar counts={data.framing as FramingCounts} className="mt-4" height="h-5" />
            <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
              {(Object.keys(FRAMING_LABELS) as (keyof FramingCounts)[]).map((key) => (
                <li key={key} className={FRAMING_TEXT[key]}>
                  {FRAMING_LABELS[key]}:{" "}
                  <span className="font-bold text-foreground">{data!.framing[key] ?? 0}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card p-5">
            <h2 className="font-serif text-lg font-bold">Claims by status</h2>
            <div className="mt-4">
              <BarChart data={data.claims_by_status} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
