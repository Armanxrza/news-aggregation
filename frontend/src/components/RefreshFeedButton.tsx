"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { triggerCrawl, getStoredAdminKey } from "@/lib/api";

export function RefreshFeedButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "ok" | "error" | "auth">("idle");

  async function handleRefresh() {
    setLoading(true);
    setStatus("idle");
    try {
      const key = getStoredAdminKey();
      if (!key) {
        setStatus("auth");
        setLoading(false);
        return;
      }
      await triggerCrawl(key);
      setStatus("ok");
      setTimeout(() => {
        router.refresh();
        setLoading(false);
      }, 2500);
    } catch {
      setStatus("error");
      setLoading(false);
    }
  }

  const label =
    loading
      ? "Crawling…"
      : status === "ok"
        ? "Crawl started"
        : status === "error"
          ? "Crawl failed"
          : status === "auth"
            ? "Set admin key"
            : "Refresh feed";

  const alert = status === "error" || status === "auth";

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        id="refresh-feed-btn"
        type="button"
        onClick={handleRefresh}
        disabled={loading}
        title="POST /api/crawl — requires admin key in Admin page"
        className={`border px-3 py-1.5 text-sm disabled:opacity-60 ${
          alert
            ? "border-accent text-accent"
            : "border-foreground/25 bg-surface text-foreground hover:border-foreground"
        }`}
      >
        {label}
      </button>
      {status === "auth" && (
        <a href="/admin" className="text-[11px] text-foreground/70 underline underline-offset-2">
          Add API key on Admin
        </a>
      )}
    </div>
  );
}
