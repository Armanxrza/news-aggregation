"use client";

import { useState } from "react";

const TOPIC_TONES: Record<string, string> = {
  Nepal: "from-[#1a3a4a] to-[#2d6a6a]",
  Politics: "from-[#3d2b3d] to-[#6b3a4a]",
  Business: "from-[#2a3540] to-[#3d5a4a]",
  Sports: "from-[#1e3a2f] to-[#3d6b4a]",
  World: "from-[#2b3040] to-[#4a5a7a]",
  Technology: "from-[#1a2a40] to-[#3a4a6a]",
  Disaster: "from-[#3a2a20] to-[#6a4a30]",
};

type Props = {
  src?: string | null;
  alt: string;
  topic?: string | null;
  className?: string;
  priority?: boolean;
};

export function NewsImage({ src, alt, topic, className = "", priority }: Props) {
  const [failed, setFailed] = useState(false);
  const tone = TOPIC_TONES[topic || ""] || "from-[#2a3540] to-[#4a5a5a]";
  const showImg = Boolean(src) && !failed;

  return (
    <div className={`relative overflow-hidden bg-slate-200 ${className}`}>
      {showImg ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src!}
          alt={alt}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <div
          className={`absolute inset-0 bg-gradient-to-br ${tone}`}
          aria-hidden
        >
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 30%, rgba(255,255,255,0.15) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(0,0,0,0.25) 0%, transparent 45%)",
            }}
          />
          <span className="absolute bottom-3 left-3 font-serif text-sm font-semibold tracking-wide text-white/70">
            {topic || "News"}
          </span>
        </div>
      )}
    </div>
  );
}
