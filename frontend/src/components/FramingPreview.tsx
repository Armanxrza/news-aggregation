"use client";

import { useState } from "react";
import { previewFraming, type FramingPreview } from "@/lib/api";
import { BiasBar } from "@/components/BiasBar";
import { framingLabel } from "@/lib/framing";

const SAMPLES = [
  "Opposition leaders criticised the cabinet for failing to deliver flood relief.",
  "The ministry published the quarterly revenue table without further comment.",
  "प्रधानमन्त्रीले नयाँ सामुदायिक अस्पताल उद्घाटन गर्दै यसलाई दिगो सार्वजनिक सेवा भने।",
];

export function FramingPreviewForm() {
  const [text, setText] = useState(SAMPLES[0]);
  const [result, setResult] = useState<FramingPreview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResult(await previewFraming(text));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Could not score that text.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 border border-border bg-surface p-5">
      <div className="space-y-1">
        <h2 className="font-serif text-lg font-semibold">Score a passage</h2>
        <p className="text-sm text-foreground/65">
          The desk classifier returns a critical, neutral, and supportive split. It does not save
          the text.
        </p>
      </div>
      <label className="block text-xs font-semibold uppercase tracking-wide text-foreground/55" htmlFor="passage">
        Passage
      </label>
      <textarea
        id="passage"
        name="passage"
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={4}
        className="w-full border border-border bg-background px-3 py-2 text-sm leading-relaxed outline-none"
      />
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((sample) => (
          <button
            key={sample}
            type="button"
            onClick={() => setText(sample)}
            className="border border-foreground/20 px-2 py-1 text-left text-xs text-foreground/70 hover:border-foreground"
          >
            {sample.slice(0, 42)}
            {sample.length > 42 ? "…" : ""}
          </button>
        ))}
      </div>
      <button
        type="submit"
        disabled={loading || text.trim().length < 12}
        className="border border-accent bg-accent px-4 py-2 text-sm font-semibold text-background disabled:opacity-50"
      >
        {loading ? "Scoring…" : "Score framing"}
      </button>
      {error && <p className="text-sm text-accent">{error}</p>}
      {result && (
        <div className="space-y-2 border-t border-border pt-4">
          <p className="text-sm font-semibold">{framingLabel(result.label)}</p>
          <BiasBar
            left={result.scores.critical * 100}
            center={result.scores.neutral * 100}
            right={result.scores.supportive * 100}
          />
          <p className="text-xs leading-relaxed text-foreground/60">{result.evidence}</p>
          <p className="text-[11px] uppercase tracking-wide text-foreground/45">
            {result.model} · {result.method}
          </p>
        </div>
      )}
    </form>
  );
}
