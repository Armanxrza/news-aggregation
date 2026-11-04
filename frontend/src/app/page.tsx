import Link from "next/link";
import { StoryCard } from "@/components/StoryCard";
import { RefreshFeedButton } from "@/components/RefreshFeedButton";
import { fetchStories } from "@/lib/api";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; lang?: string; search?: string; page?: string }>;
}) {
  const { topic, lang, search, page: pageParam } = (await searchParams) ?? {};
  const currentPage = Math.max(1, Number(pageParam) || 1);
  const pageSize = 12;
  const skip = (currentPage - 1) * pageSize;

  let fetchError = false;
  let pageData = {
    items: [] as Awaited<ReturnType<typeof fetchStories>>["items"],
    total: 0,
    has_more: false,
  };

  try {
    pageData = await fetchStories({ topic, lang, search, skip, limit: pageSize });
  } catch {
    fetchError = true;
  }

  const activeTopic = topic || "All";
  const topicLinks = ["All", "Nepal", "Politics", "Business", "Sports", "World"];
  const totalPages = Math.max(1, Math.ceil(pageData.total / pageSize));
  const [featured, ...rest] = pageData.items;

  function pageHref(page: number) {
    const params = new URLSearchParams();
    if (topic) params.set("topic", topic);
    if (lang) params.set("lang", lang);
    if (search) params.set("search", search);
    if (page > 1) params.set("page", String(page));
    const q = params.toString();
    return q ? `/?${q}` : "/";
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 border-b border-foreground/15 pb-4">
        <form action="/" method="get" className="flex min-w-0 flex-1 gap-2 sm:max-w-md">
          {topic && <input type="hidden" name="topic" value={topic} />}
          {lang && <input type="hidden" name="lang" value={lang} />}
          <input
            name="search"
            defaultValue={search}
            placeholder="Search stories"
            className="min-w-0 flex-1 border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-foreground"
          />
          <button
            type="submit"
            className="shrink-0 border border-foreground bg-foreground px-3 py-2 text-sm text-background"
          >
            Search
          </button>
        </form>
        <div className="ml-auto">
          <RefreshFeedButton />
        </div>
      </div>

      <nav className="flex flex-wrap items-baseline gap-x-4 gap-y-2 text-sm">
        {topicLinks.map((item) => {
          const params = new URLSearchParams();
          if (item !== "All") params.set("topic", item);
          if (lang) params.set("lang", lang);
          if (search) params.set("search", search);
          const href = params.toString() ? `/?${params}` : "/";
          const active = activeTopic.toLowerCase() === item.toLowerCase();
          return (
            <Link
              key={item}
              href={href}
              className={`border-b-2 pb-0.5 ${
                active
                  ? "border-accent text-foreground"
                  : "border-transparent text-foreground/60 hover:text-foreground"
              }`}
            >
              {item}
            </Link>
          );
        })}
        <span className="text-foreground/30" aria-hidden="true">
          /
        </span>
        {[
          ["All", ""],
          ["नेपाली", "ne"],
          ["EN", "en"],
        ].map(([label, value]) => {
          const params = new URLSearchParams();
          if (topic) params.set("topic", topic);
          if (search) params.set("search", search);
          if (value) params.set("lang", value);
          const href = params.toString() ? `/?${params}` : "/";
          const active = (lang || "") === value;
          return (
            <Link
              key={label}
              href={href}
              className={`border-b-2 pb-0.5 text-xs ${
                active
                  ? "border-accent text-foreground"
                  : "border-transparent text-foreground/60 hover:text-foreground"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      {fetchError ? (
        <p className="text-sm text-accent">Can’t reach the API. Start the backend on port 8000.</p>
      ) : pageData.items.length === 0 ? (
        <p className="py-12 text-sm text-foreground/55">No stories yet.</p>
      ) : (
        <div>
          {currentPage === 1 && featured && <StoryCard story={featured} featured />}
          <div>
            {(currentPage === 1 ? rest : pageData.items).map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </div>
        </div>
      )}

      {pageData.total > pageSize && (
        <nav className="flex items-center justify-center gap-4 pt-2 text-sm">
          {currentPage > 1 && (
            <Link
              href={pageHref(currentPage - 1)}
              className="underline decoration-foreground/30 underline-offset-4 hover:decoration-foreground"
            >
              Previous
            </Link>
          )}
          <span className="text-xs text-foreground/50">
            {currentPage} / {totalPages}
          </span>
          {pageData.has_more && (
            <Link
              href={pageHref(currentPage + 1)}
              className="underline decoration-foreground/30 underline-offset-4 hover:decoration-foreground"
            >
              Next
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
