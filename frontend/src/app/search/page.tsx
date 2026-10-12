import Link from "next/link";
import { Search } from "@/components/icons";
import { fetchSearch } from "@/lib/api";
import { StoryCard } from "@/components/StoryCard";
import { framingLabel } from "@/lib/framing";
import { formatTimeAgo } from "@/lib/utils";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; lang?: string }>;
}) {
  const { q, lang } = (await searchParams) ?? {};
  const query = q?.trim() ?? "";

  let result: Awaited<ReturnType<typeof fetchSearch>> | null = null;
  let error = false;

  if (query.length >= 1) {
    try {
      result = await fetchSearch(query, lang);
    } catch {
      error = true;
    }
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-serif text-3xl font-bold">Search coverage</h1>
        <p className="text-sm text-foreground/60">
          Full-text search across clustered stories and individual articles (Nepali and English).
        </p>
      </header>

      <form action="/search" method="get" className="card flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1">
          <label htmlFor="q" className="text-xs font-bold uppercase text-foreground/45">
            Query
          </label>
          <input
            id="q"
            name="q"
            defaultValue={query}
            required
            minLength={1}
            placeholder="e.g. budget, earthquake, election…"
            className="mt-1 w-full rounded-lg border border-border-subtle px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20"
          />
        </div>
        <div>
          <label htmlFor="lang" className="text-xs font-bold uppercase text-foreground/45">
            Language
          </label>
          <select
            id="lang"
            name="lang"
            defaultValue={lang ?? "all"}
            className="mt-1 block w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
          >
            <option value="all">All</option>
            <option value="ne">Nepali</option>
            <option value="en">English</option>
          </select>
        </div>
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 py-2.5 text-sm font-bold text-white hover:bg-teal-800"
        >
          <Search size={16} /> Search
        </button>
      </form>

      {!query && (
        <p className="text-sm text-foreground/50">Enter a query to search the indexed corpus.</p>
      )}

      {error && (
        <p className="card p-4 text-sm text-red-700">Search request failed. Is the API running?</p>
      )}

      {result && (
        <>
          <p className="text-sm text-foreground/55">
            Results for &ldquo;{result.query}&rdquo; — {result.stories.length} stories,{" "}
            {result.articles.length} articles
          </p>

          {result.stories.length > 0 && (
            <section className="space-y-4">
              <h2 className="font-serif text-lg font-bold">Matching stories</h2>
              <div className="grid gap-4">
                {result.stories.map((story) => (
                  <StoryCard key={story.id} story={story} />
                ))}
              </div>
            </section>
          )}

          {result.articles.length > 0 && (
            <section className="space-y-3">
              <h2 className="font-serif text-lg font-bold">Matching articles</h2>
              <ul className="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-white">
                {result.articles.map((a) => (
                  <li key={a.id} className="p-4">
                    <p className="text-xs font-bold text-teal-800">{a.source_name}</p>
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 block font-semibold hover:text-teal-800"
                    >
                      {a.original_headline}
                    </a>
                    <p className="mt-1 text-xs text-foreground/45">
                      {a.published_at ? formatTimeAgo(a.published_at) : "—"} ·{" "}
                      {framingLabel(a.government_framing)}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {result.stories.length === 0 && result.articles.length === 0 && (
            <p className="text-sm text-foreground/55">No matches found.</p>
          )}
        </>
      )}
    </div>
  );
}
