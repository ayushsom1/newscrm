import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import type {
  ExceptionQueue,
  ExceptionQueueItem,
  Kpis,
  Severity,
  Tender,
} from "@/types/dashboard";
import TendersPanel from "@/components/TendersPanel";
import JobsPanel from "@/components/JobsPanel";
import { SkeletonCard } from "@/components/Skeleton";

const SEV_LABEL: Record<Severity, string> = {
  AUTO: "AI handled",
  APPROVE: "Approve",
  HUMAN: "Needs you",
};

const SEV_BADGE: Record<Severity, string> = {
  AUTO: "bg-green-50 text-green-800 border-green-200",
  APPROVE: "bg-amber-50 text-amber-800 border-amber-200",
  HUMAN: "bg-red-50 text-brand border-red-200",
};

export default function Dashboard() {
  const [tab, setTab] = useState<Severity | "ALL">("ALL");
  const { money, locale } = useLocale();

  const kpisQ = useQuery<Kpis>({
    queryKey: ["dashboard", "kpis"],
    queryFn: async () => (await api.get("/dashboard/kpis")).data,
  });

  const queueQ = useQuery<ExceptionQueue>({
    queryKey: ["dashboard", "queue"],
    queryFn: async () => (await api.get("/dashboard/exception-queue")).data,
  });

  const tendersQ = useQuery<Tender[]>({
    queryKey: ["tenders"],
    queryFn: async () => (await api.get<Tender[]>("/tenders")).data,
  });

  const items = queueQ.data?.items ?? [];
  const filtered: ExceptionQueueItem[] =
    tab === "ALL" ? items : items.filter((i) => i.severity === tab);

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpisQ.isLoading &&
          Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}
        {kpisQ.data?.blocks.map((b) => (
          <div
            key={b.label}
            className="bg-white border border-zinc-200 rounded-lg p-4"
          >
            <div className="text-xs text-ink/60">{b.label}</div>
            <div className="mt-1 text-2xl font-semibold text-ink">
              {b.value.toLocaleString("en-IN")}
            </div>
            <div className="mt-2 text-xs text-ink/50 min-h-[1rem]">
              {b.hint ?? ""}
            </div>
          </div>
        ))}
      </div>

      {kpisQ.data && (
        <div className="text-sm text-ink/60">
          Classifieds revenue (paid + published, {locale}):{" "}
          <span className="text-ink font-medium">
            {money(kpisQ.data.revenue_running_total_inr)}
          </span>
        </div>
      )}

      {/* Exception queue */}
      <div className="bg-white border border-zinc-200 rounded-lg">
        <div className="px-4 py-3 border-b border-zinc-200 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium text-ink">Exception queue</div>
            <div className="text-xs text-ink/60">
              Derived live from the CRM. Click any row to jump to it.
            </div>
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            {(["ALL", "HUMAN", "APPROVE", "AUTO"] as const).map((t) => {
              const count =
                t === "ALL"
                  ? items.length
                  : queueQ.data?.counts[t] ?? 0;
              const active = tab === t;
              return (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`text-xs px-2.5 py-1 rounded border ${
                    active
                      ? "bg-nav text-white border-nav"
                      : "border-zinc-300 text-ink/70 hover:bg-zinc-50"
                  }`}
                >
                  {t === "ALL" ? "All" : SEV_LABEL[t]}
                  <span
                    className={`ml-1.5 text-[10px] ${
                      active ? "text-white/80" : "text-ink/50"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <ul className="divide-y divide-zinc-100">
          {queueQ.isLoading && (
            <li className="px-4 py-6 text-center text-ink/50 text-sm">
              Loading…
            </li>
          )}
          {!queueQ.isLoading && filtered.length === 0 && (
            <li className="px-4 py-8 text-center text-ink/50 text-sm">
              {tab === "ALL"
                ? "Nothing in the queue. The CRM is quiet."
                : `No items in the "${SEV_LABEL[tab as Severity]}" bucket.`}
            </li>
          )}
          {filtered.map((it, idx) => (
            <li
              key={`${it.type}-${it.ref_id}-${idx}`}
              className="px-4 py-2.5 hover:bg-zinc-50"
            >
              <Link to={it.ref_url} className="flex items-start gap-3">
                <span
                  className={`text-[10px] uppercase font-medium px-1.5 py-0.5 rounded border whitespace-nowrap ${SEV_BADGE[it.severity]}`}
                >
                  {SEV_LABEL[it.severity]}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-ink truncate">{it.summary}</div>
                  {it.detail && (
                    <div className="text-xs text-ink/50 truncate">
                      {it.detail}
                    </div>
                  )}
                </div>
                <span className="text-ink/30 text-xs">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>

      {/* Jobs */}
      <JobsPanel />

      {/* Tenders */}
      <TendersPanel tenders={tendersQ.data ?? []} loading={tendersQ.isLoading} />
    </div>
  );
}
