import type { ChurnBand } from "@/types/advertiser";

const STYLES: Record<ChurnBand, string> = {
  low: "bg-green-50 text-green-800 border-green-200",
  med: "bg-amber-50 text-amber-800 border-amber-200",
  high: "bg-red-50 text-brand border-red-200",
};

interface Props {
  band: ChurnBand | null;
  score: number | null;
}

export default function ChurnChip({ band, score }: Props) {
  if (!band) {
    return <span className="text-xs text-ink/40">—</span>;
  }
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${STYLES[band]}`}
    >
      <span className="font-medium uppercase">{band}</span>
      {score !== null && <span className="text-[10px] opacity-75">· {score}</span>}
    </span>
  );
}
