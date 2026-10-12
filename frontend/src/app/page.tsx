import Link from "next/link";
import { Search } from "@/components/icons";
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
    <div className="space-y-5 py-2">
      <div className="flex flex-wrap items-center gap-3">
        <form action="/" method="get" className="flex min-w-0 flex-1 gap-2 sm:max-w-md">
          {topic && <input type="hidden" name="topic" value={topic} />}
          {lang && <input type="hidden" name="lang" value={lang} />}
          <input
            name="search"
            defaultValue={search}
            placeholder="Search stories"
            className="min-w-0 flex-1 rounded-full border border-border-subtle bg-white px-4 py-2 text-sm shadow-sm outline-none focus:border-teal-600"
          />
          <button
            type="submit"
            aria-label="Search"
            className="rounded-full bg-[#1a2e35] p-2.5 text-white hover:bg-[#243b44]"
          >
            <Search size={16} />
          </button>
        </form>
        <div className="ml-auto">
          <RefreshFeedButton />
        </div>
      </div>

      <nav className="flex flex-wrap items-center gap-1.5">
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
              className={`rounded-full px-3 py-1 text-sm ${
                active
                  ? "bg-[#1a2e35] font-semibold text-white"
                  : "bg-white/80 text-foreground/65 hover:bg-white hover:text-foreground"
              }`}
            >
              {item}
            </Link>
          );
        })}
        <span className="mx-1 text-foreground/20">|</span>
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
              className={`text-xs font-medium ${active ? "text-teal-800" : "text-foreground/40 hover:text-foreground/70"}`}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      {fetchError ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          Can’t reach the API. Start the backend on port 8000.
        </p>
      ) : pageData.items.length === 0 ? (
        <p className="py-12 text-center text-sm text-foreground/50">No stories yet.</p>
      ) : (
        <div className="space-y-4">
          {currentPage === 1 && featured && <StoryCard story={featured} featured />}
          <div className="grid gap-3">
            {(currentPage === 1 ? rest : pageData.items).map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </div>
        </div>
      )}

      {pageData.total > pageSize && (
        <nav className="flex items-center justify-center gap-3 pt-2">
          {currentPage > 1 && (
            <Link href={pageHref(currentPage - 1)} className="text-sm font-medium text-teal-800 hover:underline">
              Previous
            </Link>
          )}
          <span className="text-xs text-foreground/40">
            {currentPage} / {totalPages}
          </span>
          {pageData.has_more && (
            <Link href={pageHref(currentPage + 1)} className="text-sm font-medium text-teal-800 hover:underline">
              Next
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
