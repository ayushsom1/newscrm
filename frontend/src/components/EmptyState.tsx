import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface Props {
  icon: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  actionTo?: string;
  /** When true, render compact inline (e.g. inside a table cell). */
  inline?: boolean;
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionTo,
  inline = false,
}: Props) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${
        inline ? "py-10" : "py-16"
      }`}
    >
      <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center text-ink/40">
        <Icon size={22} strokeWidth={1.75} />
      </div>
      <div className="mt-4 text-sm font-medium text-ink">{title}</div>
      {description && (
        <div className="mt-1 text-xs text-ink/60 max-w-xs">{description}</div>
      )}
      {actionLabel && actionTo && (
        <Link
          to={actionTo}
          className="mt-4 bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
