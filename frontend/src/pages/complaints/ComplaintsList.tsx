import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { dateOnly } from "@/lib/format";
import TriageBadge from "@/components/TriageBadge";
import { SkeletonRows } from "@/components/Skeleton";
import EmptyState from "@/components/EmptyState";
import { MessageSquareWarning } from "lucide-react";
import type { Complaint, ComplaintTriage, TriageResponse } from "@/types/complaint";
import { useAuth } from "@/lib/auth";

export default function ComplaintsList() {
  const [triageFilter, setTriageFilter] = useState<ComplaintTriage | "">("");
  const qc = useQueryClient();
  const { user } = useAuth();
  const canAct = ["ADMIN", "CIRCULATION", "SALES"].includes(user?.role ?? "");

  const { data, isLoading, isError } = useQuery<Complaint[]>({
    queryKey: ["complaints", triageFilter],
    queryFn: async () =>
      (
        await api.get<Complaint[]>("/complaints", {
          params: { triage: triageFilter || undefined },
        })
      ).data,
  });

  const triage = useMutation({
    mutationFn: async (id: number) =>
      (await api.post<TriageResponse>(`/complaints/${id}/triage`)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["complaints"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <select
          value={triageFilter}
          onChange={(e) => setTriageFilter(e.target.value as ComplaintTriage | "")}
          className="border border-zinc-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="">All triage states</option>
          <option value="PENDING">Pending triage</option>
          <option value="AUTO">Auto-resolved</option>
          <option value="ESCALATED">Escalated</option>
        </select>
        <Link
          to="/complaints/new"
          className="ml-auto bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90"
        >
          + New complaint
        </Link>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm min-w-[780px]">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Customer</th>
              <th className="text-left px-4 py-2 font-medium">Text</th>
              <th className="text-left px-4 py-2 font-medium">Channel</th>
              <th className="text-left px-4 py-2 font-medium">Triage</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {isLoading && <SkeletonRows rows={5} cols={7} />}
            {isError && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-brand">
                  Failed to load complaints.
                </td>
              </tr>
            )}
            {!isLoading && data?.length === 0 && (
              <tr>
                <td colSpan={7}>
                  <EmptyState
                    inline
                    icon={MessageSquareWarning}
                    title="No complaints yet"
                    description="Log subscriber complaints to see AI triage in action."
                    actionLabel="Log a complaint"
                    actionTo="/complaints/new"
                  />
                </td>
              </tr>
            )}
            {data?.map((c) => (
              <tr key={c.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="px-4 py-2">
                  <Link to={`/complaints/${c.id}`} className="text-ai hover:underline">
                    {c.subscriber_name}
                  </Link>
                  <div className="text-xs text-ink/50">{c.subscriber_phone ?? "—"}</div>
                </td>
                <td className="px-4 py-2 text-ink/80 max-w-sm">
                  <div className="line-clamp-2 text-xs">{c.text}</div>
                </td>
                <td className="px-4 py-2 text-ink/70">{c.channel}</td>
                <td className="px-4 py-2">
                  <TriageBadge triage={c.triage} source={c.triage_source} />
                </td>
                <td className="px-4 py-2 text-ink/70">{c.status}</td>
                <td className="px-4 py-2 text-ink/70">{dateOnly(c.created_at)}</td>
                <td className="px-4 py-2 text-right">
                  {canAct && c.triage === "PENDING" && c.status === "OPEN" && (
                    <button
                      disabled={triage.isPending}
                      onClick={() => triage.mutate(c.id)}
                      className="text-xs text-ai hover:underline"
                    >
                      Run triage
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
