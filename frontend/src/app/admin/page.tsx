"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Plus, Trash2, RefreshCw, Globe, Rss, Activity,
  FileText, Layers, CheckCircle2, AlertTriangle, X,
  ChevronRight, Loader2, ExternalLink, ShieldCheck,
} from "lucide-react";
import { API_BASE, type SourceDTO, type StatsDTO } from "@/lib/api";

// ─── tiny helpers ────────────────────────────────────────────────────────────

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

// ─── stat card ───────────────────────────────────────────────────────────────

function StatCard({
  label, value, icon: Icon, accent,
}: { label: string; value: number | string; icon: React.ElementType; accent: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex items-center gap-4 shadow-sm">
      <div className={cn("w-11 h-11 rounded-lg flex items-center justify-center shrink-0", accent)}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-extrabold text-foreground leading-none">{value}</p>
        <p className="text-xs text-foreground/50 mt-1 font-medium">{label}</p>
      </div>
    </div>
  );
}

// ─── toast ───────────────────────────────────────────────────────────────────

type ToastType = "success" | "error" | "info";
interface ToastMsg { id: number; type: ToastType; text: string }

function Toast({ msg, onDismiss }: { msg: ToastMsg; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  const colors: Record<ToastType, string> = {
    success: "bg-emerald-500",
    error:   "bg-red-500",
    info:    "bg-blue-500",
  };

  return (
    <div className={cn(
      "flex items-center gap-3 px-4 py-3 rounded-xl text-white text-sm font-medium shadow-2xl backdrop-blur-sm",
      colors[msg.type]
    )}>
      {msg.type === "success" ? <CheckCircle2 size={16} /> : msg.type === "error" ? <AlertTriangle size={16} /> : <Activity size={16} />}
      <span>{msg.text}</span>
      <button onClick={onDismiss} className="ml-auto opacity-70 hover:opacity-100"><X size={14} /></button>
    </div>
  );
}

// ─── main ────────────────────────────────────────────────────────────────────

export default function AdminPanel() {
  const [sources, setSources] = useState<SourceDTO[]>([]);
  const [stats, setStats] = useState<StatsDTO | null>(null);
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const [toastCounter, setToastCounter] = useState(0);

  // form state
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [rss, setRss] = useState("");
  const [language, setLanguage] = useState("en");
  const [bias, setBias] = useState("0");

  // ui state
  const [formLoading, setFormLoading] = useState(false);
  const [crawlState, setCrawlState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const toast = useCallback((type: ToastType, text: string) => {
    const id = toastCounter + 1;
    setToastCounter(id);
    setToasts(prev => [...prev, { id, type, text }]);
  }, [toastCounter]);

  const dismissToast = (id: number) => setToasts(prev => prev.filter(t => t.id !== id));

  // ── fetch data ──────────────────────────────────────────────────────────────
  const refreshData = useCallback(async () => {
    try {
      const [srcRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/sources`),
        fetch(`${API_BASE}/api/stats`),
      ]);
      if (srcRes.ok) setSources(await srcRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch {
      toast("error", "Could not connect to the backend.");
    }
  }, [toast]);

  useEffect(() => { refreshData(); }, [refreshData]);

  // ── add source ──────────────────────────────────────────────────────────────
  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          domain: domain.replace(/^https?:\/\//, "").replace(/\/$/, ""),
          rss_url: rss || null,
          default_bias: parseFloat(bias) || 0,
          language,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail);
      }
      toast("success", `"${name}" added successfully!`);
      setName(""); setDomain(""); setRss(""); setLanguage("en"); setBias("0");
      refreshData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "Failed to add source.");
    } finally {
      setFormLoading(false);
    }
  };

  // ── delete source ───────────────────────────────────────────────────────────
  const handleDelete = async (id: number, sourceName: string) => {
    if (!confirm(`Remove "${sourceName}" from managed portals?`)) return;
    setDeletingId(id);
    try {
      const res = await fetch(`${API_BASE}/api/sources/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
      toast("success", `"${sourceName}" removed.`);
      refreshData();
    } catch {
      toast("error", "Failed to delete source.");
    } finally {
      setDeletingId(null);
    }
  };

  // ── trigger crawl ───────────────────────────────────────────────────────────
  const handleCrawl = async () => {
    setCrawlState("running");
    try {
      const res = await fetch(`${API_BASE}/api/crawl`, { method: "POST" });
      if (!res.ok) throw new Error("Crawl failed");
      setCrawlState("done");
      toast("success", "Crawler triggered — fetching latest headlines in the background.");
      // After a moment, refresh stats to show new numbers
      setTimeout(refreshData, 3000);
    } catch {
      setCrawlState("error");
      toast("error", "Failed to trigger crawler. Is the backend running?");
    } finally {
      setTimeout(() => setCrawlState("idle"), 5000);
    }
  };

  // ── bias label ──────────────────────────────────────────────────────────────
  const biasLabel = (b: number | null) => {
    if (b === null) return "Unknown";
    if (b < -0.3) return "Left";
    if (b > 0.3) return "Right";
    return "Center";
  };

  const biasColor = (b: number | null) => {
    if (b === null) return "text-foreground/40";
    if (b < -0.3) return "text-blue-500";
    if (b > 0.3) return "text-red-500";
    return "text-gray-400";
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Toast stack */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80">
        {toasts.map(msg => (
          <Toast key={msg.id} msg={msg} onDismiss={() => dismissToast(msg.id)} />
        ))}
      </div>

      {/* Admin Header Bar */}
      <div className="border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className="text-accent" />
            <span className="font-bold text-sm text-foreground">Admin Dashboard</span>
            <span className="text-border">·</span>
            <a href="/" className="text-xs text-foreground/50 hover:text-accent transition-colors flex items-center gap-1">
              View Site <ExternalLink size={11} />
            </a>
          </div>
          <button
            id="trigger-crawler-btn"
            onClick={handleCrawl}
            disabled={crawlState === "running"}
            className={cn(
              "flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all duration-200",
              crawlState === "running" && "bg-accent/20 text-accent cursor-not-allowed",
              crawlState === "done"    && "bg-emerald-500/20 text-emerald-500",
              crawlState === "error"   && "bg-red-500/20 text-red-500",
              crawlState === "idle"    && "bg-accent text-white hover:bg-accent/90 shadow-lg shadow-accent/20",
            )}
          >
            {crawlState === "running" ? (
              <><Loader2 size={15} className="animate-spin" /> Crawling…</>
            ) : crawlState === "done" ? (
              <><CheckCircle2 size={15} /> Done!</>
            ) : crawlState === "error" ? (
              <><AlertTriangle size={15} /> Failed</>
            ) : (
              <><RefreshCw size={15} /> Run Crawler</>
            )}
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* Stats Row */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-foreground/40 mb-4">Live Statistics</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard label="Stories" value={stats?.total_stories ?? "—"} icon={Layers} accent="bg-violet-500" />
            <StatCard label="Articles" value={stats?.total_articles ?? "—"} icon={FileText} accent="bg-blue-500" />
            <StatCard label="Sources" value={stats?.total_sources ?? "—"} icon={Globe} accent="bg-cyan-500" />
            <StatCard label="Active" value={stats?.active_sources ?? "—"} icon={Activity} accent="bg-emerald-500" />
            <StatCard label="Nepali" value={stats?.nepali_sources ?? "—"} icon={Rss} accent="bg-red-500" />
          </div>
        </section>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
          {/* Add Source Form */}
          <div className="bg-surface border border-border rounded-2xl p-6 h-fit shadow-sm">
            <h2 className="text-base font-bold mb-5 flex items-center gap-2 text-foreground">
              <Plus size={18} className="text-accent" /> Add News Portal
            </h2>
            <form onSubmit={handleAddSource} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1.5 text-foreground/60 uppercase tracking-wider">Portal Name *</label>
                <input
                  type="text" required value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Online Khabar"
                  className="w-full px-3.5 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1.5 text-foreground/60 uppercase tracking-wider">Domain *</label>
                <input
                  type="text" required value={domain}
                  onChange={e => setDomain(e.target.value)}
                  placeholder="e.g. onlinekhabar.com"
                  className="w-full px-3.5 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1.5 text-foreground/60 uppercase tracking-wider">RSS Feed URL</label>
                <input
                  type="url" value={rss}
                  onChange={e => setRss(e.target.value)}
                  placeholder="https://example.com/feed"
                  className="w-full px-3.5 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1.5 text-foreground/60 uppercase tracking-wider">Language</label>
                  <select
                    value={language} onChange={e => setLanguage(e.target.value)}
                    className="w-full px-3 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                  >
                    <option value="en">English</option>
                    <option value="ne">Nepali (नेपाली)</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1.5 text-foreground/60 uppercase tracking-wider">Bias</label>
                  <select
                    value={bias} onChange={e => setBias(e.target.value)}
                    className="w-full px-3 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
                  >
                    <option value="-0.7">Far Left</option>
                    <option value="-0.4">Left</option>
                    <option value="0">Center</option>
                    <option value="0.4">Right</option>
                    <option value="0.7">Far Right</option>
                  </select>
                </div>
              </div>
              <button
                type="submit" disabled={formLoading}
                className="w-full bg-accent text-white py-2.5 rounded-lg font-bold text-sm hover:bg-accent/90 transition-all shadow-lg shadow-accent/20 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {formLoading ? <><Loader2 size={14} className="animate-spin" /> Adding…</> : <><Plus size={14} /> Save Portal</>}
              </button>
            </form>
          </div>

          {/* Source Table */}
          <div className="bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-base font-bold flex items-center gap-2 text-foreground">
                <Globe size={18} className="text-accent" />
                Managed Portals
                <span className="ml-1 text-xs font-semibold bg-accent/10 text-accent px-2 py-0.5 rounded-full">
                  {sources.length}
                </span>
              </h2>
              <button onClick={refreshData} className="text-foreground/40 hover:text-accent transition-colors p-1">
                <RefreshCw size={14} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-background/60 text-foreground/40 text-xs uppercase tracking-wider">
                    <th className="px-6 py-3 font-semibold">Portal</th>
                    <th className="px-4 py-3 font-semibold">Language</th>
                    <th className="px-4 py-3 font-semibold">Bias</th>
                    <th className="px-4 py-3 font-semibold">Crawl Type</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sources.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-foreground/40 text-sm">
                        No portals added yet.
                      </td>
                    </tr>
                  ) : (
                    sources.map(s => (
                      <tr key={s.id} className="hover:bg-background/40 transition-colors group">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-foreground">{s.name}</div>
                          <div className="text-xs text-foreground/40 flex items-center gap-1 mt-0.5">
                            <a
                              href={`https://${s.domain}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:text-accent transition-colors flex items-center gap-0.5"
                            >
                              {s.domain} <ExternalLink size={10} />
                            </a>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span className={cn(
                            "inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full",
                            s.language === "ne"
                              ? "bg-red-500/10 text-red-500"
                              : s.language === "hi"
                              ? "bg-orange-500/10 text-orange-500"
                              : "bg-blue-500/10 text-blue-500"
                          )}>
                            {s.language === "ne" ? "🇳🇵 NE" : s.language === "hi" ? "🇮🇳 HI" : "🌐 EN"}
                          </span>
                        </td>
                        <td className={cn("px-4 py-4 text-xs font-semibold", biasColor(s.default_bias))}>
                          {biasLabel(s.default_bias)}
                        </td>
                        <td className="px-4 py-4">
                          {s.rss_url ? (
                            <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-accent/10 text-accent">
                              <Rss size={10} /> RSS
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-500">
                              <Globe size={10} /> Scrape
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-4">
                          <span className={cn(
                            "inline-flex items-center gap-1.5 text-xs font-semibold",
                            s.is_active ? "text-emerald-500" : "text-foreground/30"
                          )}>
                            <span className={cn("w-1.5 h-1.5 rounded-full", s.is_active ? "bg-emerald-500 animate-pulse" : "bg-foreground/30")} />
                            {s.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <button
                            onClick={() => handleDelete(s.id, s.name)}
                            disabled={deletingId === s.id}
                            className="opacity-0 group-hover:opacity-100 text-foreground/30 hover:text-red-500 transition-all disabled:opacity-50 p-1 rounded"
                          >
                            {deletingId === s.id
                              ? <Loader2 size={14} className="animate-spin" />
                              : <Trash2 size={14} />
                            }
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* RSS URL preview strip */}
            {sources.filter(s => s.rss_url).length > 0 && (
              <div className="border-t border-border px-6 py-4">
                <p className="text-xs font-semibold text-foreground/40 uppercase tracking-wider mb-3">RSS Endpoints</p>
                <div className="space-y-2">
                  {sources.filter(s => s.rss_url).map(s => (
                    <a
                      key={s.id}
                      href={s.rss_url!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-foreground/50 hover:text-accent transition-colors group/link"
                    >
                      <Rss size={10} className="shrink-0 text-accent/60" />
                      <span className="font-medium text-foreground/70 shrink-0">{s.name}</span>
                      <ChevronRight size={10} className="text-border" />
                      <span className="truncate group-hover/link:text-accent">{s.rss_url}</span>
                      <ExternalLink size={10} className="shrink-0 opacity-0 group-hover/link:opacity-100" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick actions footer */}
        <div className="bg-surface border border-border rounded-2xl p-5 flex flex-wrap items-center gap-4">
          <div>
            <p className="text-sm font-bold text-foreground">Quick Actions</p>
            <p className="text-xs text-foreground/50 mt-0.5">Common backend operations</p>
          </div>
          <div className="flex flex-wrap gap-3 ml-auto">
            <a
              href={`${API_BASE}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-sm font-semibold text-foreground/70 hover:border-accent hover:text-accent transition-colors"
            >
              <FileText size={14} /> API Docs <ExternalLink size={11} />
            </a>
            <button
              onClick={handleCrawl}
              disabled={crawlState === "running"}
              className="flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg text-sm font-semibold text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={crawlState === "running" ? "animate-spin" : ""} />
              {crawlState === "running" ? "Crawling…" : "Re-Run Crawler"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
