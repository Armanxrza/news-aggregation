"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Trash2,
  RefreshCw,
  Globe,
  Rss,
  Activity,
  FileText,
  Layers,
  CheckCircle2,
  AlertTriangle,
  X,
  Loader2,
  ExternalLink,
  ShieldCheck,
  Key,
} from "lucide-react";
import {
  API_BASE,
  ADMIN_KEY_STORAGE,
  createSource,
  deleteSource,
  fetchCrawlRuns,
  fetchSources,
  fetchStats,
  getStoredAdminKey,
  setStoredAdminKey,
  triggerCrawl,
  updateSource,
  type CrawlRunDTO,
  type SourceDTO,
  type StatsDTO,
} from "@/lib/api";
import { cn, formatTimeAgo } from "@/lib/utils";

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", accent)}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-extrabold leading-none tabular-nums">{value}</p>
        <p className="mt-1 text-xs font-medium text-foreground/50">{label}</p>
      </div>
    </div>
  );
}

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
  const colors: Record<ToastType, string> = {
    success: "bg-emerald-600",
    error: "bg-red-600",
    info: "bg-teal-600",
  };
  return (
    <div className={cn("flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-lg", colors[msg.type])}>
      {msg.type === "success" ? <CheckCircle2 size={16} /> : msg.type === "error" ? <AlertTriangle size={16} /> : <Activity size={16} />}
      <span>{msg.text}</span>
      <button type="button" onClick={onDismiss} className="ml-auto opacity-80 hover:opacity-100">
        <X size={14} />
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

  const handleAddSource = async (e: React.FormEvent) => {
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

  return (
    <div className="space-y-8 pb-12">
      <div className="fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
        {toasts.map((msg) => (
          <Toast key={msg.id} msg={msg} onDismiss={() => dismissToast(msg.id)} />
        ))}
      </div>

      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-bold flex items-center gap-2">
            <ShieldCheck className="text-teal-700" size={28} /> Admin
          </h1>
          <p className="mt-1 text-sm text-foreground/55">Sources, crawls, and diagnostics</p>
        </div>
        <button
          type="button"
          onClick={handleCrawl}
          disabled={crawlState === "running"}
          className={cn(
            "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-bold transition-colors",
            crawlState === "running" && "cursor-not-allowed bg-teal-100 text-teal-800",
            crawlState === "done" && "bg-emerald-100 text-emerald-800",
            crawlState === "error" && "bg-red-100 text-red-800",
            crawlState === "idle" && "bg-teal-700 text-white hover:bg-teal-800",
          )}
        >
          {crawlState === "running" ? (
            <>
              <Loader2 size={15} className="animate-spin" /> Crawling…
            </>
          ) : (
            <>
              <RefreshCw size={15} /> Run crawler
            </>
          )}
        </button>
      </header>

      <section className="card p-5">
        <h2 className="flex items-center gap-2 text-sm font-bold">
          <Key size={16} className="text-teal-700" /> Admin API key
        </h2>
        <p className="mt-1 text-xs text-foreground/50">
          Stored as <code>{ADMIN_KEY_STORAGE}</code> — sent as <code>X-Admin-Key</code> on protected
          routes.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Backend ADMIN_API_KEY"
            className="min-w-0 flex-1 rounded-lg border border-border-subtle px-3 py-2 text-sm"
            autoComplete="off"
          />
          <button
            type="button"
            onClick={saveAdminKey}
            className="rounded-lg bg-foreground px-4 py-2 text-sm font-bold text-white hover:bg-slate-800"
          >
            Save key
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xs font-bold uppercase tracking-widest text-foreground/40">
          Live statistics
        </h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Stories" value={stats?.total_stories ?? "—"} icon={Layers} accent="bg-teal-600" />
          <StatCard label="Articles" value={stats?.total_articles ?? "—"} icon={FileText} accent="bg-sky-600" />
          <StatCard label="Sources" value={stats?.total_sources ?? "—"} icon={Globe} accent="bg-cyan-600" />
          <StatCard label="Active" value={stats?.active_sources ?? "—"} icon={Activity} accent="bg-emerald-600" />
          <StatCard label="Nepali" value={stats?.nepali_sources ?? "—"} icon={Rss} accent="bg-rose-600" />
          <StatCard label="Claims" value={stats?.claims ?? "—"} icon={CheckCircle2} accent="bg-amber-600" />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
        <div className="card h-fit p-6">
          <h2 className="mb-4 flex items-center gap-2 font-bold">
            <Plus size={18} className="text-teal-700" /> Add portal
          </h2>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase text-foreground/50">
                Name *
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase text-foreground/50">
                Domain *
              </label>
              <input
                required
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="onlinekhabar.com"
                className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase text-foreground/50">
                RSS URL
              </label>
              <input
                type="url"
                value={rss}
                onChange={(e) => setRss(e.target.value)}
                className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase text-foreground/50">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              >
                <option value="en">English</option>
                <option value="ne">Nepali</option>
                <option value="hi">Hindi</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={formLoading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-700 py-2.5 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              {formLoading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              Save portal
            </button>
          </form>
        </div>

        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
            <h2 className="flex items-center gap-2 font-bold">
              <Globe size={18} className="text-teal-700" /> Portals ({sources.length})
            </h2>
            <button type="button" onClick={refreshData} className="text-foreground/40 hover:text-teal-700">
              <RefreshCw size={14} />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="bg-surface-hover text-xs uppercase text-foreground/45">
                <tr>
                  <th className="px-5 py-3">Portal</th>
                  <th className="px-3 py-3">Lang</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3 w-20" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {sources.map((s) => (
                  <tr key={s.id} className="group hover:bg-surface-hover/50">
                    <td className="px-5 py-3">
                      <div className="font-semibold">{s.name}</div>
                      <a
                        href={`https://${s.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-foreground/45 hover:text-teal-700"
                      >
                        {s.domain}
                      </a>
                    </td>
                    <td className="px-3 py-3 text-xs font-bold uppercase">{s.language}</td>
                    <td className="px-3 py-3">
                      {s.rss_url ? (
                        <span className="text-xs font-semibold text-teal-700">RSS</span>
                      ) : (
                        <span className="text-xs text-foreground/45">Scrape</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => toggleActive(s)}
                        className={cn(
                          "text-xs font-semibold underline-offset-2 hover:underline",
                          s.is_active ? "text-emerald-700" : "text-foreground/40",
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
                        className="opacity-0 group-hover:opacity-100 text-foreground/30 hover:text-red-600 disabled:opacity-50"
                      >
                        {deletingId === s.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Trash2 size={14} />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <section className="card overflow-hidden">
        <div className="border-b border-border-subtle px-5 py-4">
          <h2 className="font-bold">Recent crawl runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-surface-hover text-xs uppercase text-foreground/45">
              <tr>
                <th className="px-5 py-3">Started</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">New articles</th>
                <th className="px-3 py-3">Feeds OK / fail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {crawlRuns.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-foreground/45">
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
                    <td className="px-3 py-3 tabular-nums text-xs">
                      {r.feeds_succeeded ?? 0} / {r.feeds_failed ?? 0} failed
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="card flex flex-wrap items-center gap-4 p-5">
        <p className="text-sm font-bold">API</p>
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noreferrer"
          className="ml-auto flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold hover:border-teal-600 hover:text-teal-800"
        >
          OpenAPI docs <ExternalLink size={12} />
        </a>
      </div>
    </div>
  );
}
