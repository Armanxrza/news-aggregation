"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { triggerCrawl } from "@/lib/api";

export function RefreshFeedButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "ok" | "error">("idle");

  async function handleRefresh() {
    setLoading(true);
    setStatus("idle");
    try {
      await triggerCrawl();
      setStatus("ok");
      // Give the background crawler a moment then refresh the Server Component data
      setTimeout(() => {
        router.refresh();
        setLoading(false);
      }, 2000);
    } catch {
      setStatus("error");
      setLoading(false);
    }
  }

  return (
    <button
      id="refresh-feed-btn"
      onClick={handleRefresh}
      disabled={loading}
      title="Fetch latest headlines from all RSS sources"
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition-all duration-200
        ${status === "ok"
          ? "bg-green-500/10 border-green-500/40 text-green-500"
          : status === "error"
          ? "bg-red-500/10 border-red-500/40 text-red-500"
          : "bg-accent/10 border-accent/30 text-accent hover:bg-accent/20"
        }
        disabled:opacity-60 disabled:cursor-not-allowed
      `}
    >
      <RefreshCw
        size={15}
        className={loading ? "animate-spin" : ""}
      />
      {loading ? "Refreshing…" : status === "ok" ? "Done!" : status === "error" ? "Failed" : "Refresh Feed"}
    </button>
  );
}
