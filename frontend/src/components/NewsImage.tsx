"use client";

import { useState } from "react";

type Props = {
  src?: string | null;
  alt: string;
  topic?: string | null;
  className?: string;
  priority?: boolean;
};

export function NewsImage({ src, alt, topic, className = "", priority }: Props) {
  const [failed, setFailed] = useState(false);
  const showImg = Boolean(src) && !failed;

  return (
    <div className={`relative overflow-hidden bg-foreground/10 ${className}`}>
      {showImg ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src!}
          alt={alt}
          className="absolute inset-0 h-full w-full object-cover"
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="absolute inset-0 flex items-end border border-foreground/15 bg-foreground/[0.04] p-3">
          <span className="font-serif text-sm text-foreground/45">{topic || "News"}</span>
        </div>
      )}
    </div>
  );
}
