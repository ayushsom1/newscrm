import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { money, pct } from "@/lib/format";
import ChurnChip from "@/components/ChurnChip";
import type { Advertiser } from "@/types/advertiser";

export default function AdvertiserList() {
  const [q, setQ] = useState("");
  const [band, setBand] = useState<string>("");

  const { data, isLoading, isError } = useQuery<Advertiser[]>({
    queryKey: ["advertisers", q, band],
    queryFn: async () => {
      const r = await api.get<Advertiser[]>("/advertisers", {
        params: { q: q || undefined, band: band || undefined },
      });
      return r.data;
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Advertisers</h1>
          <p className="text-sm text-ink/60">Churn band is computed by the engine.</p>
        </div>
        <Link
          to="/advertisers/new"
          className="bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90"
        >
          + New advertiser
        </Link>
      </div>

      <div className="flex items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or category…"
          className="flex-1 max-w-sm border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
        />
        <select
          value={band}
          onChange={(e) => setBand(e.target.value)}
          className="border border-zinc-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="">All churn bands</option>
          <option value="low">Low</option>
          <option value="med">Medium</option>
          <option value="high">High</option>
        </select>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Category</th>
              <th className="text-right px-4 py-2 font-medium">Annual value</th>
              <th className="text-right px-4 py-2 font-medium">Spend trend</th>
              <th className="text-right px-4 py-2 font-medium">Open rate</th>
              <th className="text-left px-4 py-2 font-medium">Churn</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-ink/50">
                  Loading…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-brand">
                  Failed to load advertisers.
                </td>
              </tr>
            )}
            {data?.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-ink/50">
                  No advertisers yet.
                </td>
              </tr>
            )}
            {data?.map((a) => (
              <tr key={a.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="px-4 py-2">
                  <Link to={`/advertisers/${a.id}`} className="text-ai hover:underline">
                    {a.name}
                  </Link>
                </td>
                <td className="px-4 py-2 text-ink/70">{a.category ?? "—"}</td>
                <td className="px-4 py-2 text-right">{money(a.annual_value)}</td>
                <td className="px-4 py-2 text-right">{pct(a.spend_trend)}</td>
                <td className="px-4 py-2 text-right">{pct(a.proposal_open_rate)}</td>
                <td className="px-4 py-2">
                  <ChurnChip band={a.churn.band} score={a.churn.score} />
                </td>
                <td className="px-4 py-2 text-ink/70">{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
