import type { ComplaintTriage } from "@/types/complaint";

const STYLES: Record<ComplaintTriage, string> = {
  PENDING: "bg-zinc-100 text-ink/80 border-zinc-200",
  AUTO: "bg-green-50 text-green-800 border-green-200",
  ESCALATED: "bg-amber-50 text-amber-800 border-amber-200",
};

interface Props {
  triage: ComplaintTriage;
  source?: string | null;
}

export default function TriageBadge({ triage, source }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${STYLES[triage]}`}
    >
      <span className="font-medium">{triage}</span>
      {source && (
        <span className={`text-[10px] opacity-75 ${source === "AI" ? "text-ai" : ""}`}>
          · {source}
        </span>
      )}
    </span>
  );
}
