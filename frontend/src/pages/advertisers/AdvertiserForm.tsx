import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Advertiser } from "@/types/advertiser";

const schema = z.object({
  name: z.string().min(1, "required"),
  category: z.string().optional(),
  contact_name: z.string().optional(),
  contact_phone: z.string().optional(),
  contact_email: z
    .string()
    .email("invalid email")
    .optional()
    .or(z.literal("")),
  annual_value: z.coerce.number().min(0, "must be >= 0").default(0),
  spend_trend: z.coerce.number().default(0),
  proposal_open_rate: z.coerce.number().min(0).max(100).default(0),
  status: z.enum(["ACTIVE", "INACTIVE", "PROSPECT"]).default("ACTIVE"),
});

type Vals = z.infer<typeof schema>;

export default function AdvertiserForm() {
  const { id } = useParams();
  const isEdit = !!id;
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data } = useQuery<Advertiser>({
    queryKey: ["advertiser", id],
    queryFn: async () => (await api.get(`/advertisers/${id}`)).data,
    enabled: isEdit,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Vals>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      annual_value: 0,
      spend_trend: 0,
      proposal_open_rate: 0,
      status: "ACTIVE",
    },
  });

  useEffect(() => {
    if (data) {
      reset({
        name: data.name,
        category: data.category ?? "",
        contact_name: data.contact_name ?? "",
        contact_phone: data.contact_phone ?? "",
        contact_email: data.contact_email ?? "",
        annual_value: Number(data.annual_value),
        spend_trend: Number(data.spend_trend),
        proposal_open_rate: Number(data.proposal_open_rate),
        status: data.status,
      });
    }
  }, [data, reset]);

  const save = useMutation({
    mutationFn: async (vals: Vals) => {
      const body = {
        ...vals,
        contact_email: vals.contact_email || null,
        annual_value: String(vals.annual_value),
        spend_trend: String(vals.spend_trend),
        proposal_open_rate: String(vals.proposal_open_rate),
      };
      if (isEdit) {
        const r = await api.patch<Advertiser>(`/advertisers/${id}`, body);
        return r.data;
      }
      const r = await api.post<Advertiser>("/advertisers", body);
      return r.data;
    },
    onSuccess: async (a) => {
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
      await qc.invalidateQueries({ queryKey: ["advertiser", String(a.id)] });
      nav(`/advertisers/${a.id}`);
    },
  });

  const submit = handleSubmit((vals) => save.mutate(vals));

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-ink mb-4">
        {isEdit ? "Edit advertiser" : "New advertiser"}
      </h1>
      <form onSubmit={submit} className="bg-white border border-zinc-200 rounded-lg p-6 space-y-4">
        <Field label="Name" error={errors.name?.message}>
          <input {...register("name")} className={input} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Category">
            <input {...register("category")} className={input} placeholder="Auto, FMCG, Real estate…" />
          </Field>
          <Field label="Status">
            <select {...register("status")} className={input}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="PROSPECT">Prospect</option>
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Contact name">
            <input {...register("contact_name")} className={input} />
          </Field>
          <Field label="Contact phone">
            <input {...register("contact_phone")} className={input} />
          </Field>
        </div>
        <Field label="Contact email" error={errors.contact_email?.message}>
          <input {...register("contact_email")} className={input} />
        </Field>

        <div className="grid grid-cols-3 gap-4">
          <Field label="Annual value (₹)" error={errors.annual_value?.message}>
            <input type="number" step="0.01" {...register("annual_value")} className={input} />
          </Field>
          <Field label="Spend trend (YoY %)" error={errors.spend_trend?.message}>
            <input type="number" step="0.1" {...register("spend_trend")} className={input} />
          </Field>
          <Field
            label="Proposal open rate (%)"
            error={errors.proposal_open_rate?.message}
          >
            <input type="number" step="0.1" {...register("proposal_open_rate")} className={input} />
          </Field>
        </div>

        {save.isError && (
          <p className="text-sm text-brand">Could not save. Check your inputs.</p>
        )}

        <div className="flex items-center gap-2">
          <button
            disabled={isSubmitting || save.isPending}
            className="bg-ink text-white text-sm px-4 py-1.5 rounded hover:bg-ink/90 disabled:opacity-60"
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={() => nav(-1)}
            className="text-sm text-ink/70 hover:text-ink px-3 py-1.5"
          >
            Cancel
          </button>
        </div>
      </form>
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
