import type { ClassifiedStatus } from "@/types/classified";

const STYLES: Record<ClassifiedStatus, string> = {
  QUOTED: "bg-zinc-100 text-ink/80 border-zinc-200",
  PAID: "bg-amber-50 text-amber-800 border-amber-200",
  PUBLISHED: "bg-green-50 text-green-800 border-green-200",
  CANCELLED: "bg-red-50 text-brand border-red-200",
};

export default function StatusBadge({ status }: { status: ClassifiedStatus }) {
  return (
    <span
      className={`inline-flex items-center text-xs px-2 py-0.5 rounded border font-medium ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
