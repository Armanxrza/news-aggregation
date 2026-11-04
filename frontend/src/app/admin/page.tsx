"use client";

import { useState, useEffect, useCallback, type FormEvent } from "react";
import {
  API_BASE,
  ADMIN_KEY_STORAGE,
  createSource,
  deleteSource,
  fetchCrawlRuns,
  fetchSources,
  fetchStats,
  getStoredAdminKey,
  resetDatabase,
  setStoredAdminKey,
  triggerCrawl,
  updateSource,
  type CrawlRunDTO,
  type SourceDTO,
  type StatsDTO,
} from "@/lib/api";
import { cn, formatTimeAgo } from "@/lib/utils";

const fieldClass =
  "w-full border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-foreground";

type ToastType = "success" | "error" | "info";
interface ToastMsg {
  id: number;
  type: ToastType;
  text: string;
}

function Toast({ msg, onDismiss }: { msg: ToastMsg; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4500);
    return () => clearTimeout(t);
  }, [onDismiss]);
  return (
    <div
      className={cn(
        "flex items-start gap-3 border bg-surface px-3 py-2 text-sm",
        msg.type === "error" ? "border-accent text-accent" : "border-foreground/20 text-foreground",
      )}
    >
      <span>{msg.text}</span>
      <button type="button" onClick={onDismiss} className="ml-auto text-xs text-foreground/50 hover:text-foreground">
        Close
      </button>
    </div>
  );
}

export default function AdminPanel() {
  const [adminKey, setAdminKey] = useState("");
  const [sources, setSources] = useState<SourceDTO[]>([]);
  const [stats, setStats] = useState<StatsDTO | null>(null);
  const [crawlRuns, setCrawlRuns] = useState<CrawlRunDTO[]>([]);
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const [toastCounter, setToastCounter] = useState(0);

  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [rss, setRss] = useState("");
  const [language, setLanguage] = useState("en");

  const [formLoading, setFormLoading] = useState(false);
  const [crawlState, setCrawlState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [resetLoading, setResetLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    setAdminKey(getStoredAdminKey());
  }, []);

  const toast = useCallback(
    (type: ToastType, text: string) => {
      const id = toastCounter + 1;
      setToastCounter(id);
      setToasts((prev) => [...prev, { id, type, text }]);
    },
    [toastCounter],
  );

  const dismissToast = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const refreshData = useCallback(async () => {
    try {
      const [src, st, runs] = await Promise.all([
        fetchSources(),
        fetchStats(),
        fetchCrawlRuns(15),
      ]);
      setSources(src);
      setStats(st);
      setCrawlRuns(runs);
    } catch {
      toast("error", "Could not connect to the backend.");
    }
  }, [toast]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  function saveAdminKey() {
    setStoredAdminKey(adminKey);
    toast("success", "Admin key saved to localStorage.");
  }

  const handleAddSource = async (e: FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await createSource(
        {
          name,
          domain: domain.replace(/^https?:\/\//, "").replace(/\/$/, ""),
          rss_url: rss || null,
          language,
        },
        adminKey,
      );
      toast("success", `"${name}" added.`);
      setName("");
      setDomain("");
      setRss("");
      setLanguage("en");
      refreshData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "Failed to add source.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id: number, sourceName: string) => {
    if (!confirm(`Remove "${sourceName}"?`)) return;
    setDeletingId(id);
    try {
      await deleteSource(id, adminKey);
      toast("success", `"${sourceName}" removed or deactivated.`);
      refreshData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setDeletingId(null);
    }
  };

  const toggleActive = async (source: SourceDTO) => {
    try {
      await updateSource(source.id, { is_active: !source.is_active }, adminKey);
      toast("info", `${source.name} is now ${source.is_active ? "inactive" : "active"}.`);
      refreshData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "Update failed.");
    }
  };

  const handleCrawl = async () => {
    if (!adminKey.trim()) {
      toast("error", "Save an admin API key first.");
      return;
    }
    setCrawlState("running");
    try {
      await triggerCrawl(adminKey);
      setCrawlState("done");
      toast("success", "Crawl started in background.");
      setTimeout(refreshData, 3000);
    } catch (err: unknown) {
      setCrawlState("error");
      toast("error", err instanceof Error ? err.message : "Crawl failed.");
    } finally {
      setTimeout(() => setCrawlState("idle"), 5000);
    }
  };

  const handleResetDb = async () => {
    if (
      !window.confirm(
        "⚠️ Reset Database?\n\nThis will wipe all existing articles, stories, claims, and crawl history, and re-seed clean sources and demo stories from scratch.",
      )
    ) {
      return;
    }
    setResetLoading(true);
    try {
      const res = await resetDatabase(adminKey || undefined);
      toast("success", `Database reset successfully! (${res.sources_seeded} sources seeded)`);
      refreshData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "Failed to reset database.");
    } finally {
      setResetLoading(false);
    }
  };

  const figures: { label: string; value: number | string }[] = [
    { label: "Stories", value: stats?.total_stories ?? "—" },
    { label: "Articles", value: stats?.total_articles ?? "—" },
    { label: "Sources", value: stats?.total_sources ?? "—" },
    { label: "Active", value: stats?.active_sources ?? "—" },
    { label: "Nepali", value: stats?.nepali_sources ?? "—" },
    { label: "Claims", value: stats?.claims ?? "—" },
  ];

  return (
    <div className="space-y-8 pb-12">
      <div className="fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
        {toasts.map((msg) => (
          <Toast key={msg.id} msg={msg} onDismiss={() => dismissToast(msg.id)} />
        ))}
      </div>

      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-foreground/20 pb-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold">Admin</h1>
          <p className="mt-1 text-sm text-foreground/60">Sources, crawls, and diagnostics</p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={handleResetDb}
            disabled={resetLoading}
            className="text-sm text-accent underline decoration-accent/40 underline-offset-4 disabled:opacity-50"
          >
            {resetLoading ? "Resetting…" : "Reset database"}
          </button>
          <button
            type="button"
            onClick={handleCrawl}
            disabled={crawlState === "running"}
            className={cn(
              "px-4 py-2 text-sm disabled:opacity-60",
              crawlState === "idle"
                ? "bg-accent text-background hover:bg-accent/90"
                : crawlState === "error"
                  ? "border border-accent text-accent"
                  : "border border-foreground text-foreground",
            )}
          >
            {crawlState === "running" ? "Crawling…" : crawlState === "done" ? "Crawl started" : "Run crawler"}
          </button>
        </div>
      </header>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Admin API key</h2>
        <p className="text-xs text-foreground/55">
          Stored as <code>{ADMIN_KEY_STORAGE}</code> — sent as <code>X-Admin-Key</code> on protected
          routes.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Backend ADMIN_API_KEY"
            className={cn(fieldClass, "min-w-0 flex-1")}
            autoComplete="off"
          />
          <button
            type="button"
            onClick={saveAdminKey}
            className="border border-foreground px-4 py-2 text-sm hover:bg-foreground hover:text-background"
          >
            Save key
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-foreground/45">
          Live statistics
        </h2>
        <dl className="grid grid-cols-2 border-y border-foreground/20 sm:grid-cols-3 lg:grid-cols-6">
          {figures.map((item) => (
            <div key={item.label} className="border-b border-foreground/10 px-3 py-3 lg:border-b-0">
              <dt className="text-xs uppercase tracking-wide text-foreground/50">{item.label}</dt>
              <dd className="mt-1 font-serif text-2xl tabular-nums">{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <div className="h-fit border border-border bg-surface p-5">
          <h2 className="mb-4 font-semibold">Add portal</h2>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-foreground/50">
                Name *
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-foreground/50">
                Domain *
              </label>
              <input
                required
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="onlinekhabar.com"
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-foreground/50">
                RSS URL
              </label>
              <input
                type="url"
                value={rss}
                onChange={(e) => setRss(e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-foreground/50">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className={fieldClass}
              >
                <option value="en">English</option>
                <option value="ne">Nepali</option>
                <option value="hi">Hindi</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={formLoading}
              className="w-full border border-foreground bg-foreground py-2.5 text-sm text-background disabled:opacity-50"
            >
              {formLoading ? "Saving…" : "Save portal"}
            </button>
          </form>
        </div>

        <div className="overflow-hidden border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="font-semibold">Portals ({sources.length})</h2>
            <button type="button" onClick={refreshData} className="text-sm text-foreground/60 underline underline-offset-2 hover:text-foreground">
              Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-foreground/15 text-xs uppercase tracking-wide text-foreground/45">
                <tr>
                  <th className="px-5 py-3 font-medium">Portal</th>
                  <th className="px-3 py-3 font-medium">Lang</th>
                  <th className="px-3 py-3 font-medium">Type</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium"> </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sources.map((s) => (
                  <tr key={s.id} className="hover:bg-background">
                    <td className="px-5 py-3">
                      <div className="font-semibold">{s.name}</div>
                      <a
                        href={`https://${s.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-foreground/50 underline decoration-foreground/20 underline-offset-2 hover:text-foreground"
                      >
                        {s.domain}
                      </a>
                    </td>
                    <td className="px-3 py-3 text-xs font-semibold uppercase">{s.language}</td>
                    <td className="px-3 py-3 text-xs text-foreground/70">
                      {s.rss_url ? "RSS" : "Scrape"}
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => toggleActive(s)}
                        className={cn(
                          "text-xs underline underline-offset-2",
                          s.is_active ? "text-foreground" : "text-foreground/45",
                        )}
                      >
                        {s.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => handleDelete(s.id, s.name)}
                        disabled={deletingId === s.id}
                        className="text-xs text-accent underline underline-offset-2 disabled:opacity-50"
                      >
                        {deletingId === s.id ? "Removing…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <section className="overflow-hidden border border-border bg-surface">
        <div className="border-b border-border px-5 py-4">
          <h2 className="font-semibold">Recent crawl runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-foreground/15 text-xs uppercase tracking-wide text-foreground/45">
              <tr>
                <th className="px-5 py-3 font-medium">Started</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-3 py-3 font-medium">New articles</th>
                <th className="px-3 py-3 font-medium">Feeds OK / fail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {crawlRuns.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-foreground/50">
                    No crawl runs recorded.
                  </td>
                </tr>
              ) : (
                crawlRuns.map((r) => (
                  <tr key={r.id}>
                    <td className="px-5 py-3 text-xs">
                      {r.started_at ? formatTimeAgo(r.started_at) : "—"}
                    </td>
                    <td className="px-3 py-3 font-semibold">{r.status ?? "—"}</td>
                    <td className="px-3 py-3 tabular-nums">{r.articles_new ?? 0}</td>
                    <td className="px-3 py-3 text-xs tabular-nums">
                      {r.feeds_succeeded ?? 0} / {r.feeds_failed ?? 0} failed
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="flex flex-wrap items-baseline gap-3 border-t border-foreground/15 pt-4 text-sm">
        <span className="font-semibold">API</span>
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noreferrer"
          className="underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground"
        >
          OpenAPI docs
        </a>
      </p>
    </div>
  );
}
