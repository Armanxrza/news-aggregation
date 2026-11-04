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
        <h1 className="font-serif text-3xl font-semibold">Search</h1>
        <p className="text-sm text-foreground/65">
          Full-text search across clustered stories and individual articles (Nepali and English).
        </p>
      </header>

      <form action="/search" method="get" className="flex flex-col gap-3 border border-border bg-surface p-4 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1">
          <label htmlFor="q" className="text-xs font-semibold uppercase tracking-wide text-foreground/45">
            Query
          </label>
          <input
            id="q"
            name="q"
            defaultValue={query}
            required
            minLength={1}
            placeholder="e.g. budget, earthquake, election…"
            className="mt-1 w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground"
          />
        </div>
        <div>
          <label htmlFor="lang" className="text-xs font-semibold uppercase tracking-wide text-foreground/45">
            Language
          </label>
          <select
            id="lang"
            name="lang"
            defaultValue={lang ?? "all"}
            className="mt-1 block w-full border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="all">All</option>
            <option value="ne">Nepali</option>
            <option value="en">English</option>
          </select>
        </div>
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-2 border border-foreground bg-foreground px-4 py-2 text-sm text-background"
        >
          <Search size={15} /> Search
        </button>
      </form>

      {!query && (
        <p className="text-sm text-foreground/55">Enter a query to search the indexed corpus.</p>
      )}

      {error && (
        <p className="text-sm text-accent">Search request failed. Is the API running?</p>
      )}

      {result && (
        <>
          <p className="text-sm text-foreground/60">
            Results for &ldquo;{result.query}&rdquo; — {result.stories.length} stories,{" "}
            {result.articles.length} articles
          </p>

          {result.stories.length > 0 && (
            <section className="space-y-4">
              <h2 className="font-serif text-xl font-semibold">Matching stories</h2>
              <div>
                {result.stories.map((story) => (
                  <StoryCard key={story.id} story={story} />
                ))}
              </div>
            </section>
          )}

          {result.articles.length > 0 && (
            <section className="space-y-3">
              <h2 className="font-serif text-xl font-semibold">Matching articles</h2>
              <ul className="divide-y divide-border border border-border bg-surface">
                {result.articles.map((a) => (
                  <li key={a.id} className="p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-foreground/55">
                      {a.source_name}
                    </p>
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 block font-semibold underline decoration-transparent underline-offset-2 hover:decoration-foreground/40"
                    >
                      {a.original_headline}
                    </a>
                    <p className="mt-1 text-xs text-foreground/50">
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
