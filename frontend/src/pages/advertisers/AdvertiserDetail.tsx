import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import type { AdvertiserDetail as AdvDetail } from "@/types/advertiser";
import { dateOnly } from "@/lib/format";
import { useLocale } from "@/lib/locale";
import ChurnChip from "@/components/ChurnChip";
import ProposalsPanel from "@/components/ProposalsPanel";
import { useAuth } from "@/lib/auth";

const contractSchema = z.object({
  start_date: z.string().min(1),
  end_date: z.string().min(1),
  value: z.coerce.number().min(0),
  slots: z.coerce.number().int().min(0).default(0),
});
type ContractVals = z.infer<typeof contractSchema>;

export default function AdvertiserDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const { money, pct, currency } = useLocale();
  const canWrite = user?.role === "ADMIN" || user?.role === "SALES";
  const canDelete = user?.role === "ADMIN";

  const { data, isLoading, isError } = useQuery<AdvDetail>({
    queryKey: ["advertiser", id],
    queryFn: async () => (await api.get(`/advertisers/${id}`)).data,
    enabled: !!id,
  });

  const addContract = useMutation({
    mutationFn: async (vals: ContractVals) => {
      const r = await api.post(`/advertisers/${id}/contracts`, {
        ...vals,
        value: String(vals.value),
        slots: vals.slots,
      });
      return r.data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["advertiser", id] });
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
      contractForm.reset();
    },
  });

  const deleteContract = useMutation({
    mutationFn: async (cid: number) =>
      await api.delete(`/advertisers/${id}/contracts/${cid}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["advertiser", id] });
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
    },
  });

  const deleteAdvertiser = useMutation({
    mutationFn: async () => await api.delete(`/advertisers/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
      nav("/advertisers");
    },
  });

  const contractForm = useForm<ContractVals>({
    resolver: zodResolver(contractSchema),
    defaultValues: { value: 0, slots: 0 },
  });

  if (isLoading) return <p className="text-sm text-ink/60">Loading…</p>;
  if (isError || !data) return <p className="text-sm text-brand">Failed to load.</p>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-ink">{data.name}</h1>
            <ChurnChip band={data.churn.band} score={data.churn.score} />
            <span className="text-xs text-ink/50">{data.status}</span>
          </div>
          <p className="text-sm text-ink/60">{data.category ?? "Uncategorised"}</p>
        </div>
        <div className="flex items-center gap-2">
          {canWrite && (
            <Link
              to={`/advertisers/${data.id}/edit`}
              className="text-sm border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50"
            >
              Edit
            </Link>
          )}
          {canDelete && (
            <button
              onClick={() => {
                if (confirm("Delete this advertiser and all contracts?")) {
                  deleteAdvertiser.mutate();
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
        <Section title="Commercial">
          <Row label="Annual value">{money(data.annual_value)}</Row>
          <Row label="Spend trend (YoY)">{pct(data.spend_trend)}</Row>
          <Row label="Proposal open rate">{pct(data.proposal_open_rate)}</Row>
        </Section>
        <Section title="Contact">
          <Row label="Name">{data.contact_name ?? "—"}</Row>
          <Row label="Phone">{data.contact_phone ?? "—"}</Row>
          <Row label="Email">{data.contact_email ?? "—"}</Row>
        </Section>
      </div>

      <Section title="Churn signals">
        {data.churn.reasons.length === 0 ? (
          <p className="text-sm text-ink/60">No risk signals — healthy account.</p>
        ) : (
          <ul className="text-sm text-ink/80 list-disc pl-5">
            {data.churn.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-ink/50">
          Computed deterministically by the churn engine. Last update:{" "}
          {data.churn.updated_at ? new Date(data.churn.updated_at).toLocaleString() : "—"}.
        </p>
      </Section>

      <ProposalsPanel advertiserId={data.id} />

      <Section title={`Contracts (${data.contracts.length})`}>
        {data.contracts.length === 0 ? (
          <p className="text-sm text-ink/60">No contracts on file.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-ink/60 uppercase">
              <tr>
                <th className="text-left py-1">Start</th>
                <th className="text-left py-1">End</th>
                <th className="text-right py-1">Value</th>
                <th className="text-right py-1">Slots</th>
                <th className="text-left py-1">Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.contracts.map((c) => (
                <tr key={c.id} className="border-t border-zinc-100">
                  <td className="py-1.5">{dateOnly(c.start_date)}</td>
                  <td className="py-1.5">{dateOnly(c.end_date)}</td>
                  <td className="py-1.5 text-right">{money(c.value)}</td>
                  <td className="py-1.5 text-right">{c.slots}</td>
                  <td className="py-1.5">{c.status}</td>
                  <td className="py-1.5 text-right">
                    {canWrite && (
                      <button
                        onClick={() => {
                          if (confirm("Delete this contract?")) {
                            deleteContract.mutate(c.id);
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
            onSubmit={contractForm.handleSubmit((v) => addContract.mutate(v))}
            className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 items-end"
          >
            <Field label="Start">
              <input type="date" {...contractForm.register("start_date")} className={input} />
            </Field>
            <Field label="End">
              <input type="date" {...contractForm.register("end_date")} className={input} />
            </Field>
            <Field label={`Value (${currency})`}>
              <input type="number" step="0.01" {...contractForm.register("value")} className={input} />
            </Field>
            <Field label="Slots">
              <input type="number" {...contractForm.register("slots")} className={input} />
            </Field>
            <button
              disabled={addContract.isPending}
              className="bg-ink text-white text-sm py-1.5 rounded hover:bg-ink/90 disabled:opacity-60"
            >
              {addContract.isPending ? "Adding…" : "Add contract"}
            </button>
          </form>
        )}
        {addContract.isError && (
          <p className="text-xs text-brand mt-2">Could not add contract.</p>
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
