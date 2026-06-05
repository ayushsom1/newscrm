import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { dateOnly, money } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";
import type { Classified, ClassifiedStatus } from "@/types/classified";
import { useAuth } from "@/lib/auth";

export default function ClassifiedsList() {
  const [statusFilter, setStatusFilter] = useState<ClassifiedStatus | "">("");
  const qc = useQueryClient();
  const { user } = useAuth();
  const canAct = ["ADMIN", "SALES", "ACCOUNTS"].includes(user?.role ?? "");

  const { data, isLoading, isError } = useQuery<Classified[]>({
    queryKey: ["classifieds", statusFilter],
    queryFn: async () => {
      const r = await api.get<Classified[]>("/classifieds", {
        params: { status: statusFilter || undefined },
      });
      return r.data;
    },
  });

  const transition = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: string }) =>
      await api.post(`/classifieds/${id}/${action}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["classifieds"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Classifieds</h1>
          <p className="text-sm text-ink/60">
            Quoted → paid → published. Price locked at booking.
          </p>
        </div>
        <Link
          to="/classifieds/new"
          className="bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90"
        >
          + New classified
        </Link>
      </div>

      <select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value as ClassifiedStatus | "")}
        className="border border-zinc-300 rounded px-3 py-1.5 text-sm"
      >
        <option value="">All statuses</option>
        <option value="QUOTED">Quoted</option>
        <option value="PAID">Paid</option>
        <option value="PUBLISHED">Published</option>
        <option value="CANCELLED">Cancelled</option>
      </select>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Customer</th>
              <th className="text-left px-4 py-2 font-medium">Text</th>
              <th className="text-left px-4 py-2 font-medium">Category</th>
              <th className="text-right px-4 py-2 font-medium">Days</th>
              <th className="text-right px-4 py-2 font-medium">Total</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Publish</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-ink/50">Loading…</td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-brand">
                  Failed to load classifieds.
                </td>
              </tr>
            )}
            {data?.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-ink/50">
                  No classifieds yet.
                </td>
              </tr>
            )}
            {data?.map((c) => (
              <tr key={c.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="px-4 py-2">
                  <div className="text-ink">{c.customer_name}</div>
                  <div className="text-xs text-ink/50">{c.customer_phone}</div>
                </td>
                <td className="px-4 py-2 text-ink/80 max-w-sm">
                  <div className="line-clamp-2 text-xs">{c.text}</div>
                  <div className="text-xs text-ink/50 mt-0.5">{c.word_count} words</div>
                </td>
                <td className="px-4 py-2 text-ink/70">{c.category}</td>
                <td className="px-4 py-2 text-right">{c.duration_days}</td>
                <td className="px-4 py-2 text-right">
                  {money(c.price_total, c.currency)}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={c.status} />
                </td>
                <td className="px-4 py-2 text-ink/70">{dateOnly(c.publish_date)}</td>
                <td className="px-4 py-2 text-right space-x-2">
                  {canAct && c.status === "QUOTED" && (
                    <button
                      disabled={transition.isPending}
                      onClick={() => transition.mutate({ id: c.id, action: "mark-paid" })}
                      className="text-xs text-ai hover:underline"
                    >
                      Mark paid
                    </button>
                  )}
                  {canAct && c.status === "PAID" && (
                    <button
                      disabled={transition.isPending}
                      onClick={() => transition.mutate({ id: c.id, action: "mark-published" })}
                      className="text-xs text-ai hover:underline"
                    >
                      Publish
                    </button>
                  )}
                  {canAct && (c.status === "QUOTED" || c.status === "PAID") && (
                    <button
                      disabled={transition.isPending}
                      onClick={() => transition.mutate({ id: c.id, action: "cancel" })}
                      className="text-xs text-brand hover:underline"
                    >
                      Cancel
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
