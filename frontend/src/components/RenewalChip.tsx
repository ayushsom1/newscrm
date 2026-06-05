import type { Severity } from "@/types/subscriber";

const STYLES: Record<Severity, string> = {
  low: "bg-green-50 text-green-800 border-green-200",
  med: "bg-amber-50 text-amber-800 border-amber-200",
  high: "bg-red-50 text-brand border-red-200",
};

interface Props {
  severity: Severity;
  daysToRenew: number | null;
}

export default function RenewalChip({ severity, daysToRenew }: Props) {
  const days = daysToRenew;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${STYLES[severity]}`}
    >
      <span className="font-medium uppercase">{severity}</span>
      {days !== null && (
        <span className="text-[10px] opacity-75">
          · {days < 0 ? `${-days}d overdue` : `${days}d`}
        </span>
      )}
    </span>
  );
}
