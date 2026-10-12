"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { RefreshCw } from "lucide-react";
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

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        id="refresh-feed-btn"
        type="button"
        onClick={handleRefresh}
        disabled={loading}
        title="POST /api/crawl — requires admin key in Admin page"
        className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-60 ${
          status === "ok"
            ? "border-emerald-300 bg-emerald-50 text-emerald-800"
            : status === "error"
              ? "border-red-300 bg-red-50 text-red-800"
              : status === "auth"
                ? "border-amber-300 bg-amber-50 text-amber-900"
                : "border-teal-200 bg-teal-50 text-teal-800 hover:bg-teal-100"
        }`}
      >
        <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
        {label}
      </button>
      {status === "auth" && (
        <a href="/admin" className="text-[11px] font-medium text-teal-700 hover:underline">
          Add API key on Admin →
        </a>
      )}
    </div>
  );
}
