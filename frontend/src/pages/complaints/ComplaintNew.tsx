import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Complaint } from "@/types/complaint";

const schema = z.object({
  subscriber_name: z.string().min(1),
  subscriber_phone: z.string().optional(),
  area: z.string().optional(),
  text: z.string().min(3),
  channel: z.enum(["PHONE", "EMAIL", "WHATSAPP", "WALK_IN"]),
});
type Vals = z.infer<typeof schema>;

export default function ComplaintNew() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Vals>({
    resolver: zodResolver(schema),
    defaultValues: { channel: "PHONE" },
  });

  const save = useMutation({
    mutationFn: async (vals: Vals) => {
      const r = await api.post<Complaint>("/complaints", {
        ...vals,
        subscriber_phone: vals.subscriber_phone || null,
        area: vals.area || null,
      });
      return r.data;
    },
    onSuccess: async (c) => {
      await qc.invalidateQueries({ queryKey: ["complaints"] });
      nav(`/complaints/${c.id}`);
    },
  });

  return (
    <div className="max-w-2xl">
      <form
        onSubmit={handleSubmit((v) => save.mutate(v))}
        className="bg-white border border-zinc-200 rounded-lg p-6 space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Subscriber name" error={errors.subscriber_name?.message}>
            <input {...register("subscriber_name")} className={input} />
          </Field>
          <Field label="Phone">
            <input {...register("subscriber_phone")} className={input} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Area">
            <input {...register("area")} className={input} placeholder="Patan, Lalitpur…" />
          </Field>
          <Field label="Channel">
            <select {...register("channel")} className={input}>
              <option value="PHONE">Phone</option>
              <option value="EMAIL">Email</option>
              <option value="WHATSAPP">WhatsApp</option>
              <option value="WALK_IN">Walk-in</option>
            </select>
          </Field>
        </div>
        <Field label="Complaint text" error={errors.text?.message}>
          <textarea rows={5} {...register("text")} className={input} />
          <p className="text-xs text-ink/50 mt-1">
            Triage runs as a separate step after creation.
          </p>
        </Field>

        {save.isError && (
          <p className="text-sm text-brand">Could not save complaint.</p>
        )}

        <div className="flex items-center gap-2">
          <button
            disabled={isSubmitting || save.isPending}
            className="bg-ink text-white text-sm px-4 py-1.5 rounded hover:bg-ink/90 disabled:opacity-60"
          >
            {save.isPending ? "Saving…" : "Save complaint"}
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
