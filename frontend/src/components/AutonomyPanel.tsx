import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { showSuccess } from "@/lib/toast";
import type { Autonomy } from "@/types/settings";

interface ToggleSpec {
  key: keyof Pick<
    Autonomy,
    | "triage_ai_enabled"
    | "triage_auto_resolve_enabled"
    | "ai_draft_enabled"
    | "high_churn_always_needs_human"
    | "assistant_actions_require_admin"
  >;
  label: string;
  helper: string;
  whenOff?: string;
}

const TOGGLES: ToggleSpec[] = [
  {
    key: "triage_ai_enabled",
    label: "AI complaint triage",
    helper:
      "Use the model to classify routine vs. sensitive complaints. When off, the deterministic engine handles all triage.",
    whenOff: "All triage goes through keyword rules.",
  },
  {
    key: "triage_auto_resolve_enabled",
    label: "Auto-resolve routine triage",
    helper:
      "When on, routine triage (non-delivery, pause, plan change) is marked RESOLVED automatically.",
    whenOff: "All triaged complaints stay OPEN for a human to close.",
  },
  {
    key: "ai_draft_enabled",
    label: "AI proposal drafting",
    helper:
      "Lets sales staff click 'Draft with AI' on an advertiser. The deterministic engine template is always available as a fallback.",
    whenOff: "AI drafting is disabled; only the engine template is used.",
  },
  {
    key: "high_churn_always_needs_human",
    label: "High-churn drafts always need a human",
    helper:
      "Flags every draft for a high-churn advertiser as needs_human, so it cannot be one-click approved.",
    whenOff: "Disabling this removes a critical safety net — keep on in production.",
  },
  {
    key: "assistant_actions_require_admin",
    label: "Assistant actions require ADMIN to approve",
    helper:
      "When on, only admins can approve the assistant's proposed actions. Otherwise any SALES/CIRCULATION user can.",
  },
];

export default function AutonomyPanel() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const aQ = useQuery<Autonomy>({
    queryKey: ["autonomy"],
    queryFn: async () => (await api.get<Autonomy>("/settings/autonomy")).data,
  });

  const patch = useMutation({
    mutationFn: async (body: Partial<Autonomy>) =>
      (await api.patch<Autonomy>("/settings/autonomy", body)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["autonomy"] });
      showSuccess("Settings updated");
    },
  });

  if (aQ.isLoading || !aQ.data) {
    return <p className="text-sm text-ink/60">Loading…</p>;
  }
  const a = aQ.data;

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="bg-white border border-zinc-200 rounded-lg divide-y divide-zinc-100">
        {TOGGLES.map((t) => {
          const value = a[t.key];
          return (
            <div
              key={t.key}
              className="flex items-start justify-between p-4 gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-ink">{t.label}</div>
                <div className="text-xs text-ink/60 mt-0.5">{t.helper}</div>
                {!value && t.whenOff && (
                  <div className="text-xs text-amber-700 mt-1">
                    Currently off: {t.whenOff}
                  </div>
                )}
              </div>
              <Toggle
                checked={value}
                disabled={!isAdmin || patch.isPending}
                onChange={(next) => patch.mutate({ [t.key]: next })}
              />
            </div>
          );
        })}

        <div className="p-4 flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="text-sm font-medium text-ink">Locale</div>
            <div className="text-xs text-ink/60 mt-0.5">
              Drives currency and tax labels (IN → ₹/GST, NP → NPR/VAT).
            </div>
          </div>
          <select
            disabled={!isAdmin || patch.isPending}
            value={a.locale}
            onChange={(e) => patch.mutate({ locale: e.target.value })}
            className="border border-zinc-300 rounded px-3 py-1.5 text-sm disabled:opacity-50"
          >
            <option value="IN">India (₹/GST)</option>
            <option value="NP">Nepal (NPR/VAT)</option>
          </select>
        </div>
      </div>

      <p className="text-xs text-ink/50">
        Last updated{" "}
        {new Date(a.updated_at).toLocaleString()}
        {a.updated_by_id ? ` · by user #${a.updated_by_id}` : ""}.
      </p>

      {!isAdmin && (
        <p className="text-xs text-ink/50">
          Only admins can change these. You're viewing them read-only.
        </p>
      )}
    </div>
  );
}

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition disabled:opacity-50 ${
        checked ? "bg-nav" : "bg-zinc-300"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}
