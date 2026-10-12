import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, Rss } from "lucide-react";
import { fetchSourceDetail } from "@/lib/api";
import { framingLabel, perspectiveLabel } from "@/lib/framing";
import { SourceFramingHistory } from "@/components/SourceFramingHistory";
import { formatTimeAgo } from "@/lib/utils";

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sourceId = Number(id);
  if (!Number.isInteger(sourceId)) notFound();

  let source;
  try {
    source = await fetchSourceDetail(sourceId);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-8">
      <Link
        href="/sources"
        className="inline-flex items-center gap-2 text-sm font-semibold text-foreground/60 hover:text-teal-800"
      >
        <ArrowLeft size={16} /> All sources
      </Link>

      <header className="card space-y-4 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold">{source.name}</h1>
            <a
              href={`https://${source.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-sm text-teal-700 hover:underline"
            >
              {source.domain} <ExternalLink size={14} />
            </a>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
              source.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
            }`}
          >
            {source.is_active ? "Active" : "Inactive"}
          </span>
        </div>

        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          <div>
            <dt className="text-xs font-bold uppercase text-foreground/45">Language</dt>
            <dd className="mt-1 font-semibold">{source.language?.toUpperCase() ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase text-foreground/45">Perspective</dt>
            <dd className="mt-1">{perspectiveLabel(source.perspective_label)}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase text-foreground/45">Articles crawled</dt>
            <dd className="mt-1 font-semibold tabular-nums">{source.article_count}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase text-foreground/45">Last crawl</dt>
            <dd className="mt-1">
              {source.last_crawl_at ? formatTimeAgo(source.last_crawl_at) : "—"}
              {source.last_crawl_status && (
                <span className="text-foreground/45"> ({source.last_crawl_status})</span>
              )}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-bold uppercase text-foreground/45">Framing history</dt>
            <dd className="mt-2">
              <SourceFramingHistory history={source.framing_history} />
            </dd>
          </div>
        </dl>

        {source.rss_url && (
          <p className="flex items-center gap-2 text-xs text-foreground/55">
            <Rss size={14} className="text-teal-700" />
            <a href={source.rss_url} target="_blank" rel="noreferrer" className="truncate hover:text-teal-700">
              {source.rss_url}
            </a>
          </p>
        )}

        {source.ownership_notes && (
          <div className="border-t border-border-subtle pt-4 text-sm text-foreground/65">
            <p className="text-xs font-bold uppercase text-foreground/45">Ownership notes</p>
            <p className="mt-1">{source.ownership_notes}</p>
          </div>
        )}
      </header>

      <section>
        <h2 className="mb-4 font-serif text-xl font-bold">Recent articles</h2>
        {source.recent_articles.length === 0 ? (
          <p className="text-sm text-foreground/55">No articles indexed yet.</p>
        ) : (
          <ul className="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-white">
            {source.recent_articles.map((a) => (
              <li key={a.id} className="p-4 hover:bg-surface-hover/40">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold leading-snug hover:text-teal-800"
                >
                  {a.original_headline}
                </a>
                <p className="mt-1 text-xs text-foreground/50">
                  {a.published_at ? formatTimeAgo(a.published_at) : "—"} ·{" "}
                  {framingLabel(a.government_framing)}
                </p>
                {a.snippet && <p className="mt-2 text-sm text-foreground/60 line-clamp-2">{a.snippet}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
