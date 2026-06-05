import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { money } from "@/lib/format";
import { CATEGORIES, type Classified, type Quote } from "@/types/classified";

const schema = z.object({
  customer_name: z.string().min(1, "required"),
  customer_phone: z.string().min(4, "required"),
  text: z.string().min(1, "required"),
  category: z.enum(CATEGORIES),
  duration_days: z.coerce.number().int().min(1).max(365),
  locale: z.enum(["IN", "NP"]).default("IN"),
  publish_date: z.string().optional(),
});

type Vals = z.infer<typeof schema>;

export default function ClassifiedNew() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { locale: defaultLocale } = useLocale();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<Vals>({
    resolver: zodResolver(schema),
    defaultValues: {
      duration_days: 1,
      category: "GENERAL",
      locale: defaultLocale,
    },
  });

  const watched = useWatch({ control });

  // Debounced live quote.
  useEffect(() => {
    const text = watched.text ?? "";
    const category = watched.category ?? "GENERAL";
    const duration = Number(watched.duration_days ?? 1);
    const locale = (watched.locale ?? "IN") as "IN" | "NP";
    if (!text.trim() || duration < 1) {
      setQuote(null);
      setQuoteError(null);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = await api.post<Quote>("/classifieds/quote", {
          text,
          category,
          duration_days: duration,
          locale,
        });
        setQuote(r.data);
        setQuoteError(null);
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          "could not quote";
        setQuote(null);
        setQuoteError(msg);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [watched.text, watched.category, watched.duration_days, watched.locale]);

  const book = useMutation({
    mutationFn: async (vals: Vals) => {
      const r = await api.post<Classified>("/classifieds", {
        ...vals,
        publish_date: vals.publish_date || null,
      });
      return r.data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["classifieds"] });
      nav("/classifieds");
    },
  });

  return (
    <div className="max-w-5xl">
      <h1 className="text-xl font-semibold text-ink mb-4">New classified</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <form
          onSubmit={handleSubmit((v) => book.mutate(v))}
          className="lg:col-span-2 bg-white border border-zinc-200 rounded-lg p-6 space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Field label="Customer name" error={errors.customer_name?.message}>
              <input {...register("customer_name")} className={input} />
            </Field>
            <Field label="Phone" error={errors.customer_phone?.message}>
              <input {...register("customer_phone")} className={input} />
            </Field>
          </div>

          <Field label="Ad text" error={errors.text?.message}>
            <textarea {...register("text")} rows={5} className={input} />
            <p className="text-xs text-ink/50 mt-1">
              Word count is computed deterministically by the pricing engine.
            </p>
          </Field>

          <div className="grid grid-cols-4 gap-4">
            <Field label="Category">
              <select {...register("category")} className={input}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Duration (days)" error={errors.duration_days?.message}>
              <input type="number" min={1} {...register("duration_days")} className={input} />
            </Field>
            <Field label="Locale">
              <select {...register("locale")} className={input}>
                <option value="IN">India (₹/GST)</option>
                <option value="NP">Nepal (NPR/VAT)</option>
              </select>
            </Field>
            <Field label="Publish date">
              <input type="date" {...register("publish_date")} className={input} />
            </Field>
          </div>

          {book.isError && (
            <p className="text-sm text-brand">Could not book. Check your inputs.</p>
          )}

          <div className="flex items-center gap-2">
            <button
              disabled={isSubmitting || book.isPending || !quote}
              className="bg-ink text-white text-sm px-4 py-1.5 rounded hover:bg-ink/90 disabled:opacity-50"
            >
              {book.isPending ? "Booking…" : "Book at quoted price"}
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

        <aside className="bg-white border border-zinc-200 rounded-lg p-6 space-y-3 self-start">
          <div className="text-sm font-medium text-ink">Live quote</div>
          {quoteError && <p className="text-sm text-brand">{quoteError}</p>}
          {!quote && !quoteError && (
            <p className="text-sm text-ink/50">
              Start typing — the deterministic pricing engine quotes in real time.
            </p>
          )}
          {quote && (
            <div className="space-y-2 text-sm">
              <Row label="Words">{quote.word_count}</Row>
              <Row label="Per-day rate">
                {money(quote.breakdown.per_day, quote.currency)}
              </Row>
              <Row label="Days">{quote.breakdown.days}</Row>
              <Row label="Gross">{money(quote.breakdown.gross, quote.currency)}</Row>
              <Row label={`Discount`}>{quote.breakdown.discount_pct}%</Row>
              <div className="border-t border-zinc-100 my-2" />
              <Row label="Net">{money(quote.net, quote.currency)}</Row>
              <Row label={`${quote.tax_label} (${quote.breakdown.tax_rate_pct}%)`}>
                {money(quote.tax, quote.currency)}
              </Row>
              <Row label="Total" strong>
                {money(quote.total, quote.currency)}
              </Row>
              <p className="text-[11px] text-ink/40 pt-2">
                Engine-computed, not AI. Locked into the booking on submit.
              </p>
            </div>
          )}
        </aside>
      </div>
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

function Row({
  label,
  children,
  strong,
}: {
  label: string;
  children: React.ReactNode;
  strong?: boolean;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-ink/60">{label}</span>
      <span className={strong ? "font-semibold text-ink" : "text-ink"}>{children}</span>
    </div>
  );
}
