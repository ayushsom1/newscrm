import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Tender } from "@/types/dashboard";
import { dateOnly } from "@/lib/format";
import { useLocale } from "@/lib/locale";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  title: z.string().min(1),
  department: z.string().min(1),
  deadline: z.string().min(1),
  est_value: z.coerce.number().min(0),
});
type Vals = z.infer<typeof schema>;

const STATUS_STYLES: Record<Tender["status"], string> = {
  OPEN: "bg-amber-50 text-amber-800 border-amber-200",
  SUBMITTED: "bg-blue-50 text-ai border-blue-200",
  WON: "bg-green-50 text-green-800 border-green-200",
  LOST: "bg-red-50 text-brand border-red-200",
  CLOSED: "bg-zinc-100 text-ink/60 border-zinc-200",
};

interface Props {
  tenders: Tender[];
  loading: boolean;
}

export default function TendersPanel({ tenders, loading }: Props) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { money, currency } = useLocale();
  const canWrite = user?.role === "ADMIN" || user?.role === "SALES";
  const [showForm, setShowForm] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Vals>({ resolver: zodResolver(schema) });

  const add = useMutation({
    mutationFn: async (vals: Vals) =>
      (
        await api.post("/tenders", {
          ...vals,
          est_value: String(vals.est_value),
        })
      ).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["tenders"] });
      await qc.invalidateQueries({ queryKey: ["dashboard", "queue"] });
      reset();
      setShowForm(false);
    },
  });

  const transition = useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: number;
      status: Tender["status"];
    }) => (await api.patch(`/tenders/${id}`, { status })).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["tenders"] });
      await qc.invalidateQueries({ queryKey: ["dashboard", "queue"] });
    },
  });

  return (
    <div className="bg-white border border-zinc-200 rounded-lg">
      <div className="px-4 py-3 border-b border-zinc-200 flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-ink">
            Government / DIPR tenders
          </div>
          <div className="text-xs text-ink/60">
            Manual entry now; ingestion in a later sprint.
          </div>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="text-xs border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
          >
            {showForm ? "Cancel" : "+ Add tender"}
          </button>
        )}
      </div>

      {showForm && canWrite && (
        <form
          onSubmit={handleSubmit((v) => add.mutate(v))}
          className="border-b border-zinc-100 p-4 grid grid-cols-1 md:grid-cols-5 gap-2 items-end"
        >
          <Field label="Title" error={errors.title?.message}>
            <input {...register("title")} className={input} />
          </Field>
          <Field label="Department" error={errors.department?.message}>
            <input {...register("department")} className={input} />
          </Field>
          <Field label="Deadline" error={errors.deadline?.message}>
            <input type="date" {...register("deadline")} className={input} />
          </Field>
          <Field label={`Est. value (${currency})`} error={errors.est_value?.message}>
            <input
              type="number"
              step="0.01"
              {...register("est_value")}
              className={input}
            />
          </Field>
          <button
            disabled={isSubmitting || add.isPending}
            className="bg-ink text-white text-sm py-1.5 rounded hover:bg-ink/90 disabled:opacity-60"
          >
            {add.isPending ? "Saving…" : "Save"}
          </button>
        </form>
      )}

      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-ink/60 text-xs uppercase">
          <tr>
            <th className="text-left px-4 py-2 font-medium">Title</th>
            <th className="text-left px-4 py-2 font-medium">Department</th>
            <th className="text-left px-4 py-2 font-medium">Deadline</th>
            <th className="text-right px-4 py-2 font-medium">Est. value</th>
            <th className="text-left px-4 py-2 font-medium">Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-ink/50">
                Loading…
              </td>
            </tr>
          )}
          {!loading && tenders.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-ink/50">
                No tenders tracked yet.
              </td>
            </tr>
          )}
          {tenders.map((t) => (
            <tr key={t.id} className="border-t border-zinc-100">
              <td className="px-4 py-2 text-ink">{t.title}</td>
              <td className="px-4 py-2 text-ink/70">{t.department}</td>
              <td className="px-4 py-2 text-ink/70">{dateOnly(t.deadline)}</td>
              <td className="px-4 py-2 text-right">{money(t.est_value)}</td>
              <td className="px-4 py-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded border ${STATUS_STYLES[t.status]}`}
                >
                  {t.status}
                </span>
              </td>
              <td className="px-4 py-2 text-right space-x-2">
                {canWrite && t.status === "OPEN" && (
                  <button
                    onClick={() =>
                      transition.mutate({ id: t.id, status: "SUBMITTED" })
                    }
                    className="text-xs text-ai hover:underline"
                  >
                    Mark submitted
                  </button>
                )}
                {canWrite && t.status === "SUBMITTED" && (
                  <>
                    <button
                      onClick={() =>
                        transition.mutate({ id: t.id, status: "WON" })
                      }
                      className="text-xs text-green-700 hover:underline"
                    >
                      Won
                    </button>
                    <button
                      onClick={() =>
                        transition.mutate({ id: t.id, status: "LOST" })
                      }
                      className="text-xs text-brand hover:underline"
                    >
                      Lost
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const input =
  "w-full border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40";

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-ink/70">{label}</label>
      {children}
      {error && <p className="text-xs text-brand">{error}</p>}
    </div>
  );
}
