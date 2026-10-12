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
        <h1 className="font-serif text-3xl font-bold">Source directory</h1>
        <p className="max-w-2xl text-sm text-foreground/60">
          Registered RSS and scrape outlets. Framing history reflects government-framing labels on
          crawled articles — not editorial endorsement scores.
        </p>
        {!error && (
          <p className="text-xs text-foreground/45">
            {sources.length} outlets · {active} active
          </p>
        )}
      </header>

      {error ? (
        <p className="card p-6 text-sm text-red-700">Could not load sources from the API.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border-subtle bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-surface-hover text-xs uppercase text-foreground/50">
              <tr>
                <th className="px-4 py-3 font-semibold">Outlet</th>
                <th className="px-4 py-3 font-semibold">Language</th>
                <th className="px-4 py-3 font-semibold">Perspective</th>
                <th className="px-4 py-3 font-semibold">Framing history</th>
                <th className="px-4 py-3 font-semibold">Articles</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {sources.map((s) => (
                <tr key={s.id} className="hover:bg-surface-hover/40">
                  <td className="px-4 py-3">
                    <Link href={`/sources/${s.id}`} className="font-semibold text-teal-800 hover:underline">
                      {s.name}
                    </Link>
                    <p className="text-xs text-foreground/45">{s.domain}</p>
                  </td>
                  <td className="px-4 py-3 uppercase text-xs font-bold text-foreground/55">
                    {s.language ?? "—"}
                  </td>
                  <td className="max-w-[180px] px-4 py-3 text-xs text-foreground/60">
                    {perspectiveLabel(s.perspective_label)}
                  </td>
                  <td className="px-4 py-3">
                    <SourceFramingHistory history={s.framing_history} />
                  </td>
                  <td className="px-4 py-3 tabular-nums">{s.article_count}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                        s.is_active ? "text-emerald-700" : "text-foreground/35"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          s.is_active ? "bg-emerald-500" : "bg-slate-300"
                        }`}
                      />
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
