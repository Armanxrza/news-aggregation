"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { analyzeStoryClaims, getStoredAdminKey } from "@/lib/api";

export function AnalyzeClaimsButton({ storyId }: { storyId: number }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function run() {
    const key = getStoredAdminKey();
    if (!key) {
      setMessage("Save your admin API key on the Admin page first.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const result = await analyzeStoryClaims(storyId, key);
      setMessage(`Processed ${result.processed_articles} articles · ${result.claims.length} claims.`);
      router.refresh();
    } catch (e) {
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
        className="inline-flex items-center gap-2 rounded-lg border border-teal-600 bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700 disabled:opacity-60"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
        Analyze claims
      </button>
      {message && <p className="text-xs text-foreground/60">{message}</p>}
    </div>
  );
}
