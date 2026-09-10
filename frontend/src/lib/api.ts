/**
 * Typed API client for the SajhaNews backend.
 * All fetch calls go through here so the base URL is managed in one place.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "https://api.sajhanews.yagyatech.com.np";

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export interface StoryDTO {
  id: number;
  ai_headline: string;
  ai_summary: string | null;
  topic: string | null;
  bias_left_pct: number;
  bias_center_pct: number;
  bias_right_pct: number;
  created_at: string;
  source_count: number;
  thumbnail_url: string | null;
  sources: string[];
  languages: string[];
}

export interface ArticleDTO {
  id: number;
  source_name: string;
  source_domain: string;
  source_language: string;
  source_bias: number | null;
  original_headline: string;
  url: string;
  thumbnail_url: string | null;
  published_at: string | null;
  snippet: string | null;
}

export interface StoryDetailDTO extends StoryDTO {
  articles: ArticleDTO[];
}

export interface SourceDTO {
  id: number;
  name: string;
  domain: string;
  rss_url: string | null;
  default_bias: number | null;
  language: string | null;
  is_active: boolean;
}

export interface StatsDTO {
  total_stories: number;
  total_articles: number;
  total_sources: number;
  active_sources: number;
  nepali_sources: number;
}

export interface TopicDTO {
  topic: string;
  count: number;
}

export interface FetchStoriesParams {
  topic?: string;
  lang?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

export async function fetchStories(params?: FetchStoriesParams): Promise<StoryDTO[]> {
  const url = new URL(`${API_BASE}/api/stories`);
  if (params?.topic && params.topic.toLowerCase() !== "all") {
    url.searchParams.set("topic", params.topic);
  }
  if (params?.lang && params.lang.toLowerCase() !== "all") {
    url.searchParams.set("lang", params.lang);
  }
  if (params?.search && params.search.trim()) {
    url.searchParams.set("search", params.search.trim());
  }
  if (typeof params?.skip === "number") {
    url.searchParams.set("skip", String(params.skip));
  }
  if (typeof params?.limit === "number") {
    url.searchParams.set("limit", String(params.limit));
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`GET /api/stories failed: ${res.status}`);
  return res.json();
}

export async function fetchTopics(): Promise<TopicDTO[]> {
  const res = await fetch(`${API_BASE}/api/topics`, {
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  }).catch(() => null);
  if (!res || !res.ok) return [];
  return res.json();
}

export async function fetchStoryDetail(id: number): Promise<StoryDetailDTO> {
  const res = await fetch(`${API_BASE}/api/stories/${id}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`GET /api/stories/${id} failed: ${res.status}`);
  return res.json();
}

export async function fetchSources(): Promise<SourceDTO[]> {
  const res = await fetch(`${API_BASE}/api/sources`, {
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`GET /api/sources failed: ${res.status}`);
  return res.json();
}

export async function fetchStats(): Promise<StatsDTO> {
  const res = await fetch(`${API_BASE}/api/stats`, {
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`GET /api/stats failed: ${res.status}`);
  return res.json();
}

export async function createSource(payload: Omit<SourceDTO, "id" | "is_active">): Promise<SourceDTO> {
  const res = await fetch(`${API_BASE}/api/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Failed to create source");
  }
  return res.json();
}

export async function deleteSource(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/sources/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE /api/sources/${id} failed: ${res.status}`);
}

export async function triggerCrawl(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/crawl`, { method: "POST" });
  if (!res.ok) throw new Error(`POST /api/crawl failed: ${res.status}`);
  return res.json();
}
