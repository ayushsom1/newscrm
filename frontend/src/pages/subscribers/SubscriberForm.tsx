import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { showSuccess } from "@/lib/toast";
import type { Subscriber } from "@/types/subscriber";
import { PLANS } from "@/types/subscriber";

const schema = z.object({
  name: z.string().min(1),
  phone: z.string().min(4),
  area: z.string().min(1),
  address: z.string().optional(),
  plan: z.enum(["DAILY", "WEEKEND", "SUNDAY_ONLY"]),
  status: z.enum(["ACTIVE", "PAUSED", "CANCELLED"]),
  missed_payments: z.coerce.number().int().min(0),
});

type Vals = z.infer<typeof schema>;

export default function SubscriberForm() {
  const { id } = useParams();
  const isEdit = !!id;
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data } = useQuery<Subscriber>({
    queryKey: ["subscriber", id],
    queryFn: async () => (await api.get(`/subscribers/${id}`)).data,
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
      plan: "DAILY",
      status: "ACTIVE",
      missed_payments: 0,
    },
  });

  useEffect(() => {
    if (data) {
      reset({
        name: data.name,
        phone: data.phone,
        area: data.area,
        address: data.address ?? "",
        plan: data.plan,
        status: data.status,
        missed_payments: data.missed_payments,
      });
    }
  }, [data, reset]);

  const save = useMutation({
    mutationFn: async (vals: Vals) => {
      const body = { ...vals, address: vals.address || null };
      if (isEdit) {
        const r = await api.patch<Subscriber>(`/subscribers/${id}`, body);
        return r.data;
      }
      const r = await api.post<Subscriber>("/subscribers", body);
      return r.data;
    },
    onSuccess: async (s) => {
      await qc.invalidateQueries({ queryKey: ["subscribers"] });
      await qc.invalidateQueries({ queryKey: ["subscriber", String(s.id)] });
      showSuccess(isEdit ? `Updated ${s.name}` : `Created ${s.name}`);
      nav(`/subscribers/${s.id}`);
    },
  });

  const errMsg =
    save.isError &&
    ((save.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      "could not save");

  return (
    <div className="max-w-2xl">
      <form
        onSubmit={handleSubmit((v) => save.mutate(v))}
        className="bg-white border border-zinc-200 rounded-lg p-6 space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Name" error={errors.name?.message}>
            <input {...register("name")} className={input} />
          </Field>
          <Field label="Phone" error={errors.phone?.message}>
            <input {...register("phone")} className={input} />
          </Field>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Area" error={errors.area?.message}>
            <input {...register("area")} className={input} placeholder="e.g. Patan" />
          </Field>
          <Field label="Address">
            <input {...register("address")} className={input} />
          </Field>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Plan">
            <select {...register("plan")} className={input}>
              {PLANS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select {...register("status")} className={input}>
              <option value="ACTIVE">Active</option>
              <option value="PAUSED">Paused</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </Field>
          <Field label="Missed payments">
            <input type="number" min={0} {...register("missed_payments")} className={input} />
          </Field>
        </div>

        {errMsg && <p className="text-sm text-brand">{String(errMsg)}</p>}

        <div className="flex items-center gap-2">
          <button
            disabled={isSubmitting || save.isPending}
            className="bg-nav text-white text-sm px-4 py-1.5 rounded hover:bg-nav-darker disabled:opacity-60"
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
