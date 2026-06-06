import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import RenewalChip from "@/components/RenewalChip";
import { SkeletonRows } from "@/components/Skeleton";
import EmptyState from "@/components/EmptyState";
import { Users } from "lucide-react";
import type { Subscriber } from "@/types/subscriber";

export default function SubscribersList() {
  const [q, setQ] = useState("");
  const [atRisk, setAtRisk] = useState<"" | "true" | "false">("");

  const { data, isLoading, isError } = useQuery<Subscriber[]>({
    queryKey: ["subscribers", q, atRisk],
    queryFn: async () => {
      const r = await api.get<Subscriber[]>("/subscribers", {
        params: {
          q: q || undefined,
          at_risk: atRisk || undefined,
        },
      });
      return r.data;
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or phone…"
          className="max-w-sm flex-1 border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
        />
        <select
          value={atRisk}
          onChange={(e) => setAtRisk(e.target.value as "" | "true" | "false")}
          className="border border-zinc-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="">All subscribers</option>
          <option value="true">At-risk only</option>
          <option value="false">Healthy only</option>
        </select>
        <Link
          to="/subscribers/forecast"
          className="ml-auto text-sm border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
        >
          Print-run forecast
        </Link>
        <Link
          to="/subscribers/new"
          className="bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90"
        >
          + New subscriber
        </Link>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm min-w-[680px]">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Phone</th>
              <th className="text-left px-4 py-2 font-medium">Area</th>
              <th className="text-left px-4 py-2 font-medium">Plan</th>
              <th className="text-left px-4 py-2 font-medium">Renewal</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <SkeletonRows rows={6} cols={6} />}
            {isError && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-brand">
                  Failed to load subscribers.
                </td>
              </tr>
            )}
            {!isLoading && data?.length === 0 && (
              <tr>
                <td colSpan={6}>
                  <EmptyState
                    inline
                    icon={Users}
                    title="No subscribers yet"
                    description="Add subscribers to power the renewal engine and print-run forecast."
                    actionLabel="Add a subscriber"
                    actionTo="/subscribers/new"
                  />
                </td>
              </tr>
            )}
            {data?.map((s) => (
              <tr key={s.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="px-4 py-2">
                  <Link to={`/subscribers/${s.id}`} className="text-ai hover:underline">
                    {s.name}
                  </Link>
                </td>
                <td className="px-4 py-2 text-ink/70">{s.phone}</td>
                <td className="px-4 py-2 text-ink/70">{s.area}</td>
                <td className="px-4 py-2 text-ink/70">{s.plan}</td>
                <td className="px-4 py-2">
                  <RenewalChip
                    severity={s.renewal.severity}
                    daysToRenew={s.renewal.days_to_renew}
                  />
                </td>
                <td className="px-4 py-2 text-ink/70">{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
