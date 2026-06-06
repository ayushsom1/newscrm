import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { dateOnly, money } from "@/lib/format";
import { showSuccess } from "@/lib/toast";
import StatusBadge from "@/components/StatusBadge";
import { SkeletonRows } from "@/components/Skeleton";
import EmptyState from "@/components/EmptyState";
import { Newspaper } from "lucide-react";
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
    onSuccess: async (_data, { action }) => {
      await qc.invalidateQueries({ queryKey: ["classifieds"] });
      const label =
        action === "mark-paid"
          ? "Marked as paid"
          : action === "mark-published"
            ? "Published"
            : "Cancelled";
      showSuccess(label);
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
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
        <Link
          to="/classifieds/new"
          className="ml-auto bg-nav text-white text-sm px-3 py-1.5 rounded hover:bg-nav-darker"
        >
          + New classified
        </Link>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm min-w-[860px]">
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
              <SkeletonRows
                rows={5}
                cols={8}
                align={["left", "left", "left", "right", "right", "left", "left", "right"]}
              />
            )}
            {isError && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-brand">
                  Failed to load classifieds.
                </td>
              </tr>
            )}
            {!isLoading && data?.length === 0 && (
              <tr>
                <td colSpan={8}>
                  <EmptyState
                    inline
                    icon={Newspaper}
                    title="No classifieds yet"
                    description="Book a classified to see it move through Quoted → Paid → Published."
                    actionLabel="Book a classified"
                    actionTo="/classifieds/new"
                  />
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
