import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ForecastSummary } from "@/types/subscriber";

export default function Forecast() {
  const { data, isLoading, isError } = useQuery<ForecastSummary>({
    queryKey: ["subscribers", "forecast"],
    queryFn: async () => (await api.get("/subscribers/forecast")).data,
  });

  if (isLoading) return <p className="text-sm text-ink/60">Loading…</p>;
  if (isError || !data)
    return <p className="text-sm text-brand">Failed to load forecast.</p>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-semibold text-ink">Print-run forecast</h1>
        <p className="text-sm text-ink/60">
          Engine-computed from active subs × historical returns per area.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card label="Active subscribers" value={data.total_active} />
        <Card label="Target copies / day" value={data.total_target} accent />
        <Card label="Areas covered" value={data.areas.length} />
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Area</th>
              <th className="text-right px-4 py-2 font-medium">Active subs</th>
              <th className="text-right px-4 py-2 font-medium">Returns %</th>
              <th className="text-right px-4 py-2 font-medium">Target</th>
            </tr>
          </thead>
          <tbody>
            {data.areas.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-ink/50">
                  No active subscribers yet.
                </td>
              </tr>
            )}
            {data.areas.map((a) => (
              <tr key={a.area} className="border-t border-zinc-100">
                <td className="px-4 py-2">{a.area}</td>
                <td className="px-4 py-2 text-right">{a.active_subs}</td>
                <td className="px-4 py-2 text-right">{a.returns_pct.toFixed(1)}%</td>
                <td className="px-4 py-2 text-right font-medium">{a.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-ink/50">
        Returns % is seeded per area; tune in Settings once subscribers history is loaded.
      </p>
    </div>
  );
}

function Card({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4">
      <div className="text-xs text-ink/60">{label}</div>
      <div
        className={`mt-1 text-2xl font-semibold ${accent ? "text-ai" : "text-ink"}`}
      >
        {value.toLocaleString("en-IN")}
      </div>
    </div>
  );
}
