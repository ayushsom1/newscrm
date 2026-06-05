import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import RenewalChip from "@/components/RenewalChip";
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
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Subscribers</h1>
          <p className="text-sm text-ink/60">
            At-risk flag is computed by the renewal engine.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/subscribers/forecast"
            className="text-sm border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
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
      </div>

      <div className="flex items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or phone…"
          className="flex-1 max-w-sm border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
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
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
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
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-ink/50">Loading…</td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-brand">
                  Failed to load subscribers.
                </td>
              </tr>
            )}
            {data?.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-ink/50">
                  No subscribers yet.
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
