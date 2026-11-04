"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { analyzeStoryClaims, getStoredAdminKey } from "@/lib/api";

export function AnalyzeClaimsButton({ storyId }: { storyId: number }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  async function run() {
    const key = getStoredAdminKey();
    if (!key) {
      setFailed(true);
      setMessage("Save your admin API key on the Admin page first.");
      return;
    }
    setLoading(true);
    setMessage(null);
    setFailed(false);
    try {
      const result = await analyzeStoryClaims(storyId, key);
      setMessage(`Processed ${result.processed_articles} articles · ${result.claims.length} claims.`);
      router.refresh();
    } catch (e) {
      setFailed(true);
      setMessage(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={run}
        disabled={loading}
        className="border border-foreground bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-60"
      >
        {loading ? "Analyzing…" : "Analyze claims"}
      </button>
      {message && (
        <p className={`text-xs ${failed ? "text-accent" : "text-foreground/60"}`}>{message}</p>
      )}
    </div>
  );
}
