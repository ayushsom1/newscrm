import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import RenewalChip from "@/components/RenewalChip";
import type { SubscriberDetail as Detail } from "@/types/subscriber";
import { PLANS } from "@/types/subscriber";
import { dateOnly, money } from "@/lib/format";
import { useAuth } from "@/lib/auth";

const subSchema = z.object({
  plan: z.enum(["DAILY", "WEEKEND", "SUNDAY_ONLY"]),
  start_date: z.string().min(1),
  renew_date: z.string().min(1),
  monthly_price: z.coerce.number().min(0),
});
type SubVals = z.infer<typeof subSchema>;

export default function SubscriberDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "CIRCULATION";
  const canDelete = user?.role === "ADMIN";

  const { data, isLoading, isError } = useQuery<Detail>({
    queryKey: ["subscriber", id],
    queryFn: async () => (await api.get(`/subscribers/${id}`)).data,
    enabled: !!id,
  });

  const addSub = useMutation({
    mutationFn: async (vals: SubVals) =>
      (
        await api.post(`/subscribers/${id}/subscriptions`, {
          ...vals,
          monthly_price: String(vals.monthly_price),
        })
      ).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["subscriber", id] });
      await qc.invalidateQueries({ queryKey: ["subscribers"] });
      subForm.reset();
    },
  });

  const deleteSub = useMutation({
    mutationFn: async (subId: number) =>
      await api.delete(`/subscribers/${id}/subscriptions/${subId}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["subscriber", id] });
      await qc.invalidateQueries({ queryKey: ["subscribers"] });
    },
  });

  const deleteSubscriber = useMutation({
    mutationFn: async () => await api.delete(`/subscribers/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["subscribers"] });
      nav("/subscribers");
    },
  });

  const subForm = useForm<SubVals>({
    resolver: zodResolver(subSchema),
    defaultValues: { plan: "DAILY", monthly_price: 0 },
  });

  if (isLoading) return <p className="text-sm text-ink/60">Loading…</p>;
  if (isError || !data) return <p className="text-sm text-brand">Failed to load.</p>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-ink">{data.name}</h1>
            <RenewalChip
              severity={data.renewal.severity}
              daysToRenew={data.renewal.days_to_renew}
            />
            <span className="text-xs text-ink/50">{data.status}</span>
          </div>
          <p className="text-sm text-ink/60">
            {data.area} · {data.plan}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canWrite && (
            <Link
              to={`/subscribers/${data.id}/edit`}
              className="text-sm border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
            >
              Edit
            </Link>
          )}
          {canDelete && (
            <button
              onClick={() => {
                if (confirm("Delete this subscriber and all subscriptions?")) {
                  deleteSubscriber.mutate();
                }
              }}
              className="text-sm text-brand border border-red-200 px-3 py-1.5 rounded hover:bg-red-50"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section title="Contact">
          <Row label="Phone">{data.phone}</Row>
          <Row label="Address">{data.address ?? "—"}</Row>
        </Section>
        <Section title="Account">
          <Row label="Missed payments">{data.missed_payments}</Row>
          <Row label="Created">{dateOnly(data.created_at)}</Row>
        </Section>
      </div>

      <Section title="Renewal signals">
        {data.renewal.reasons.length === 0 ? (
          <p className="text-sm text-ink/60">No risk signals.</p>
        ) : (
          <ul className="text-sm text-ink/80 list-disc pl-5">
            {data.renewal.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-ink/50">
          Computed by the renewal engine. Not AI.
        </p>
      </Section>

      <Section title={`Subscriptions (${data.subscriptions.length})`}>
        {data.subscriptions.length === 0 ? (
          <p className="text-sm text-ink/60">None on file.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-ink/60 uppercase">
              <tr>
                <th className="text-left py-1">Plan</th>
                <th className="text-left py-1">Start</th>
                <th className="text-left py-1">Renews</th>
                <th className="text-right py-1">Monthly</th>
                <th className="text-left py-1">Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.subscriptions.map((s) => (
                <tr key={s.id} className="border-t border-zinc-100">
                  <td className="py-1.5">{s.plan}</td>
                  <td className="py-1.5">{dateOnly(s.start_date)}</td>
                  <td className="py-1.5">{dateOnly(s.renew_date)}</td>
                  <td className="py-1.5 text-right">{money(s.monthly_price)}</td>
                  <td className="py-1.5">{s.status}</td>
                  <td className="py-1.5 text-right">
                    {canWrite && (
                      <button
                        onClick={() => {
                          if (confirm("Delete this subscription?")) {
                            deleteSub.mutate(s.id);
                          }
                        }}
                        className="text-xs text-brand hover:underline"
                      >
                        delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {canWrite && (
          <form
            onSubmit={subForm.handleSubmit((v) => addSub.mutate(v))}
            className="mt-4 grid grid-cols-5 gap-2 items-end"
          >
            <Field label="Plan">
              <select {...subForm.register("plan")} className={input}>
                {PLANS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Start">
              <input type="date" {...subForm.register("start_date")} className={input} />
            </Field>
            <Field label="Renews">
              <input type="date" {...subForm.register("renew_date")} className={input} />
            </Field>
            <Field label="Monthly (₹)">
              <input
                type="number"
                step="0.01"
                {...subForm.register("monthly_price")}
                className={input}
              />
            </Field>
            <button
              disabled={addSub.isPending}
              className="bg-ink text-white text-sm py-1.5 rounded hover:bg-ink/90 disabled:opacity-60"
            >
              {addSub.isPending ? "Adding…" : "Add"}
            </button>
          </form>
        )}
      </Section>
    </div>
  );
}

const input =
  "w-full border border-zinc-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4">
      <div className="text-sm font-medium text-ink mb-2">{title}</div>
      {children}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-ink/60">{label}</span>
      <span className="text-ink">{children}</span>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-ink/60">{label}</label>
      {children}
    </div>
  );
}
