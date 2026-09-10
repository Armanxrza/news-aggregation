import React from 'react';
import { cn } from '@/lib/utils';

interface BiasBarProps {
  left: number; // percentage 0-100
  center: number;
  right: number;
  className?: string;
}

export function BiasBar({ left, center, right, className }: BiasBarProps) {
  // Normalize if they don't add up to 100 perfectly due to rounding
  const total = left + center + right;
  const l = total > 0 ? (left / total) * 100 : 33.3;
  const c = total > 0 ? (center / total) * 100 : 33.4;
  const r = total > 0 ? (right / total) * 100 : 33.3;

  return (
    <div className={cn("w-full h-2 rounded-full overflow-hidden flex bg-border/50 gap-0.5", className)}>
      <div 
        style={{ width: `${l}%` }} 
        className="h-full bg-[var(--color-bias-left)] transition-all duration-500" 
      />
      <div 
        style={{ width: `${c}%` }} 
        className="h-full bg-[var(--color-bias-center)] transition-all duration-500" 
      />
      <div 
        style={{ width: `${r}%` }} 
        className="h-full bg-[var(--color-bias-right)] transition-all duration-500" 
      />
    </div>
  );
}
