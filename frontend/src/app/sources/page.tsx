import Link from "next/link";
import { fetchSources } from "@/lib/api";
import { perspectiveLabel } from "@/lib/framing";
import { SourceFramingHistory } from "@/components/SourceFramingHistory";

export default async function SourcesPage() {
  let sources: Awaited<ReturnType<typeof fetchSources>> = [];
  let error = false;
  try {
    sources = await fetchSources();
  } catch {
    error = true;
  }

  const active = sources.filter((s) => s.is_active).length;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-serif text-3xl font-semibold">Source directory</h1>
        <p className="max-w-2xl text-sm text-foreground/65">
          Registered RSS and scrape outlets. Framing history reflects government-framing labels on
          crawled articles — not editorial endorsement scores.
        </p>
        {!error && (
          <p className="text-xs text-foreground/50">
            {sources.length} outlets · {active} active
          </p>
        )}
      </header>

      {error ? (
        <p className="text-sm text-accent">Could not load sources from the API.</p>
      ) : (
        <div className="overflow-x-auto border border-border bg-surface">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-foreground/20 text-xs uppercase tracking-wide text-foreground/50">
              <tr>
                <th className="px-4 py-3 font-medium">Outlet</th>
                <th className="px-4 py-3 font-medium">Language</th>
                <th className="px-4 py-3 font-medium">Perspective</th>
                <th className="px-4 py-3 font-medium">Framing history</th>
                <th className="px-4 py-3 font-medium">Articles</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sources.map((s) => (
                <tr key={s.id} className="hover:bg-background">
                  <td className="px-4 py-3">
                    <Link href={`/sources/${s.id}`} className="font-semibold underline decoration-foreground/25 underline-offset-2 hover:decoration-foreground">
                      {s.name}
                    </Link>
                    <p className="text-xs text-foreground/50">{s.domain}</p>
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold uppercase text-foreground/60">
                    {s.language ?? "—"}
                  </td>
                  <td className="max-w-[180px] px-4 py-3 text-xs text-foreground/65">
                    {perspectiveLabel(s.perspective_label)}
                  </td>
                  <td className="px-4 py-3">
                    <SourceFramingHistory history={s.framing_history} />
                  </td>
                  <td className="px-4 py-3 tabular-nums">{s.article_count}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${s.is_active ? "text-foreground" : "text-foreground/40"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
