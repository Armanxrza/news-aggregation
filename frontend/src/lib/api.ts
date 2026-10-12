/**
 * Typed API client for the SajhaNews backend.
 */

const rawApiBase = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").trim();
export const API_BASE = (
  rawApiBase.startsWith("http://") || rawApiBase.startsWith("https://") || rawApiBase.startsWith("/")
    ? rawApiBase
    : `https://${rawApiBase}`
).replace(/\/+$/, "");

export const ADMIN_KEY_STORAGE = "sajhanews_admin_key";

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export type FramingCounts = {
  government_critical: number;
  government_neutral: number;
  government_supportive: number;
  insufficient_evidence: number;
  analysis_unavailable: number;
  unclassified: number;
};

export interface StoryDTO {
  id: number;
  ai_headline: string;
  ai_summary: string | null;
  topic: string | null;
  bias_left_pct: number | null;
  bias_center_pct: number | null;
  bias_right_pct: number | null;
  bias_axis?: "government_pov" | string;
  gov_counts?: { critical: number; neutral: number; supportive: number };
  source_bias?: {
    source: string;
    pov: string;
    scores?: { critical: number; neutral: number; supportive: number };
  }[];
  created_at: string;
  source_count: number;
  article_count: number;
  thumbnail_url: string | null;
  sources: string[];
  languages: string[];
  framing_counts: FramingCounts;
  cluster_method: string | null;
  cluster_confidence: number | null;
}

export interface HeadlineComparisonRow {
  source: string;
  language: string | null;
  headline: string;
  framing: string | null;
  bias?: string | null;
  url: string;
}

export interface ClaimDTO {
  id: number;
  article_id: number | null;
  story_id: number | null;
  claim_text: string;
  status: "supported" | "contradicted" | "disputed" | "unverified";
  confidence: number | null;
  evidence: Record<string, unknown>;
  model: string | null;
  created_at: string | null;
}

export interface CoverageGapOutlet {
  id: number;
  name: string;
  domain: string;
  language: string | null;
}

export interface StoryDetailDTO extends StoryDTO {
  articles: ArticleDTO[];
  headline_comparison: HeadlineComparisonRow[];
  claims: ClaimDTO[];
  coverage_gap: CoverageGapOutlet[];
  methodology_note: string;
}

export interface ArticleDTO {
  id: number;
  source_name: string;
  source_domain: string;
  source_language: string;
  source_bias: null;
  perspective_label: string | null;
  original_headline: string;
  url: string;
  thumbnail_url: string | null;
  published_at: string | null;
  snippet: string | null;
  political_bias: "left" | "center" | "right" | null;
  bias_confidence: number | null;
  bias_evidence: string | null;
  bias_model: string | null;
  government_framing: string | null;
  framing_confidence: number | null;
  framing_model: string | null;
  framing_evidence: string | null;
  framing_method: string | null;
  entities: string[];
  topics: string[];
  signals: Record<string, unknown>;
}

export interface SourceDTO {
  id: number;
  name: string;
  domain: string;
  rss_url: string | null;
  default_bias: number | null;
  language: string | null;
  is_active: boolean;
  category: string | null;
  ownership_notes: string | null;
  transparency_notes: string | null;
  perspective_label: string;
  perspective_confidence: number | null;
  perspective_evidence: string | null;
  last_crawl_at: string | null;
  last_crawl_status: string | null;
  last_error: string | null;
  article_count: number;
  framing_history: Record<string, number> | null;
}

export interface SourceDetailDTO extends SourceDTO {
  recent_articles: ArticleDTO[];
}

export interface StatsDTO {
  total_stories: number;
  total_articles: number;
  total_sources: number;
  active_sources: number;
  nepali_sources: number;
  claims: number;
  crawl_runs: number;
}

export interface TopicDTO {
  topic: string;
  count: number;
}

export interface CoverageDistributionDTO {
  total_articles: number;
  classified_articles: number;
  today_articles: number;
  latest_published_at: string | null;
  counts: FramingCounts & {
    insufficient_evidence?: number;
    analysis_unavailable?: number;
  };
  bias_counts?: { left: number; center: number; right: number };
}

export interface StoriesPageDTO {
  items: StoryDTO[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface SearchResultDTO {
  query: string;
  stories: StoryDTO[];
  articles: ArticleDTO[];
}

export interface AnalyticsOverviewDTO {
  articles_by_language: Record<string, number>;
  articles_by_topic: Record<string, number>;
  framing: FramingCounts;
  claims_by_status: Record<string, number>;
  sources_active: number;
  sources_total: number;
  last_crawl: {
    id: number;
    started_at: string | null;
    status: string | null;
    articles_new: number | null;
    feeds_failed: number | null;
  } | null;
}

export interface CrawlRunDTO {
  id: number;
  started_at: string | null;
  finished_at: string | null;
  status: string | null;
  feeds_attempted: number | null;
  feeds_succeeded: number | null;
  feeds_failed: number | null;
  articles_new: number | null;
  errors: unknown[];
}

export interface FetchStoriesParams {
  topic?: string;
  lang?: string;
  search?: string;
  skip?: number;
  limit?: number;
  min_sources?: number;
}

export interface SourceCreatePayload {
  name: string;
  domain: string;
  rss_url?: string | null;
  language?: string;
  category?: string;
  ownership_notes?: string | null;
  perspective_label?: string;
}

export interface SourceUpdatePayload {
  name?: string;
  rss_url?: string | null;
  language?: string;
  is_active?: boolean;
  category?: string;
  ownership_notes?: string | null;
  perspective_label?: string | null;
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    cache: init?.cache ?? "no-store",
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      typeof err.detail === "string" ? err.detail : `Request failed: ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

/** Client-side admin requests with X-Admin-Key from localStorage. */
export async function adminFetch<T>(
  path: string,
  init: RequestInit = {},
  adminKey?: string | null,
): Promise<T> {
  const key =
    adminKey ??
    (typeof window !== "undefined"
      ? localStorage.getItem(ADMIN_KEY_STORAGE)
      : null);
  const headers = new Headers(init.headers);
  if (key) headers.set("X-Admin-Key", key);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return apiFetch<T>(path, { ...init, headers });
}

export function getStoredAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(ADMIN_KEY_STORAGE) || "";
}

export function setStoredAdminKey(key: string): void {
  if (typeof window === "undefined") return;
  if (key.trim()) localStorage.setItem(ADMIN_KEY_STORAGE, key.trim());
  else localStorage.removeItem(ADMIN_KEY_STORAGE);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch("/api/health");
}

export async function fetchStories(
  params?: FetchStoriesParams,
): Promise<StoriesPageDTO> {
  const url = new URL(`${API_BASE}/api/stories`);
  if (params?.topic && params.topic.toLowerCase() !== "all") {
    url.searchParams.set("topic", params.topic);
  }
  if (params?.lang && params.lang.toLowerCase() !== "all") {
    url.searchParams.set("lang", params.lang);
  }
  if (params?.search?.trim()) {
    url.searchParams.set("search", params.search.trim());
  }
  if (typeof params?.skip === "number") {
    url.searchParams.set("skip", String(params.skip));
  }
  if (typeof params?.limit === "number") {
    url.searchParams.set("limit", String(params.limit));
  }
  if (typeof params?.min_sources === "number") {
    url.searchParams.set("min_sources", String(params.min_sources));
  }
  return apiFetch(url.pathname + url.search);
}

export async function fetchTopics(): Promise<TopicDTO[]> {
  try {
    return await apiFetch("/api/topics");
  } catch {
    return [];
  }
}

export async function fetchCoverageDistribution(): Promise<CoverageDistributionDTO> {
  return apiFetch("/api/coverage-distribution");
}

export async function fetchStoryDetail(id: number): Promise<StoryDetailDTO> {
  return apiFetch(`/api/stories/${id}`);
}

export async function fetchSources(): Promise<SourceDTO[]> {
  return apiFetch("/api/sources");
}

export async function fetchSourceDetail(id: number): Promise<SourceDetailDTO> {
  return apiFetch(`/api/sources/${id}`);
}

export async function fetchStats(): Promise<StatsDTO> {
  return apiFetch("/api/stats");
}

export async function fetchSearch(
  q: string,
  lang?: string,
): Promise<SearchResultDTO> {
  const url = new URL(`${API_BASE}/api/search`);
  url.searchParams.set("q", q);
  if (lang && lang.toLowerCase() !== "all") {
    url.searchParams.set("lang", lang);
  }
  return apiFetch(url.pathname + url.search);
}

export async function fetchAnalyticsOverview(): Promise<AnalyticsOverviewDTO> {
  return apiFetch("/api/analytics/overview");
}

export async function fetchClaims(params?: {
  status?: string;
  story_id?: number;
}): Promise<ClaimDTO[]> {
  const url = new URL(`${API_BASE}/api/claims`);
  if (params?.status) url.searchParams.set("status", params.status);
  if (params?.story_id) url.searchParams.set("story_id", String(params.story_id));
  return apiFetch(url.pathname + url.search);
}

export async function fetchCrawlRuns(limit = 20): Promise<CrawlRunDTO[]> {
  return apiFetch(`/api/crawl-runs?limit=${limit}`);
}

export async function triggerCrawl(adminKey?: string | null): Promise<{ message: string }> {
  if (typeof window !== "undefined") {
    return adminFetch("/api/crawl", { method: "POST" }, adminKey);
  }
  const key = process.env.ADMIN_API_KEY;
  const headers: HeadersInit = {};
  if (key) headers["X-Admin-Key"] = key;
  return apiFetch("/api/crawl", { method: "POST", headers });
}

export async function createSource(
  payload: SourceCreatePayload,
  adminKey?: string | null,
): Promise<SourceDTO> {
  return adminFetch(
    "/api/sources",
    { method: "POST", body: JSON.stringify(payload) },
    adminKey,
  );
}

export async function updateSource(
  id: number,
  payload: SourceUpdatePayload,
  adminKey?: string | null,
): Promise<SourceDTO> {
  return adminFetch(
    `/api/sources/${id}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    adminKey,
  );
}

export async function deleteSource(
  id: number,
  adminKey?: string | null,
): Promise<void> {
  await adminFetch(`/api/sources/${id}`, { method: "DELETE" }, adminKey);
}

export async function analyzeStoryClaims(
  storyId: number,
  adminKey?: string | null,
): Promise<{ processed_articles: number; claims: ClaimDTO[] }> {
  return adminFetch(
    `/api/stories/${storyId}/analyze-claims`,
    { method: "POST" },
    adminKey,
  );
}

export async function analyzeArticleFraming(
  articleId: number,
  adminKey?: string | null,
): Promise<ArticleDTO> {
  return adminFetch(
    `/api/articles/${articleId}/analyze-framing`,
    { method: "POST" },
    adminKey,
  );
}
