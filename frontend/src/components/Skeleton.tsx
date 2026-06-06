import { useId } from "react";

interface SkeletonRowsProps {
  rows?: number;
  cols: number;
  /** Inline-flex alignment classes per column. */
  align?: ("left" | "right")[];
}

/** Placeholder rows for a <table>, matching the column count so layout doesn't shift. */
export function SkeletonRows({ rows = 5, cols, align }: SkeletonRowsProps) {
  const base = useId();
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={`${base}-${r}`} className="border-t border-zinc-100">
          {Array.from({ length: cols }).map((_, c) => {
            const a = align?.[c] ?? "left";
            return (
              <td key={c} className="px-4 py-3">
                <span
                  className={`block h-3 rounded bg-zinc-200/80 animate-pulse ${
                    a === "right" ? "ml-auto w-16" : ""
                  } ${a === "left" ? "w-3/4 max-w-[16rem]" : ""}`}
                  aria-hidden="true"
                />
              </td>
            );
          })}
        </tr>
      ))}
    </>
  );
}

/** Card-shaped skeleton. */
export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-white border border-zinc-200 rounded-lg p-4 ${className}`}
      aria-hidden="true"
    >
      <div className="h-3 w-24 rounded bg-zinc-200/80 animate-pulse" />
      <div className="mt-3 h-6 w-16 rounded bg-zinc-200/80 animate-pulse" />
      <div className="mt-3 h-2 w-32 rounded bg-zinc-200/70 animate-pulse" />
    </div>
  );
}
