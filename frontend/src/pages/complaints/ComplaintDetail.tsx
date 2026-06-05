import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { dateOnly } from "@/lib/format";
import TriageBadge from "@/components/TriageBadge";
import type { Complaint, TriageResponse } from "@/types/complaint";
import { useAuth } from "@/lib/auth";

export default function ComplaintDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const canAct = ["ADMIN", "CIRCULATION", "SALES"].includes(user?.role ?? "");
  const [resolution, setResolution] = useState("");

  const { data, isLoading, isError } = useQuery<Complaint>({
    queryKey: ["complaint", id],
    queryFn: async () => (await api.get(`/complaints/${id}`)).data,
    enabled: !!id,
  });

  const triage = useMutation({
    mutationFn: async () =>
      (await api.post<TriageResponse>(`/complaints/${id}/triage`)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["complaint", id] });
      await qc.invalidateQueries({ queryKey: ["complaints"] });
    },
  });

  const resolve = useMutation({
    mutationFn: async () =>
      (await api.post<Complaint>(`/complaints/${id}/resolve`, { resolution })).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["complaint", id] });
      await qc.invalidateQueries({ queryKey: ["complaints"] });
      setResolution("");
    },
  });

  if (isLoading) return <p className="text-sm text-ink/60">Loading…</p>;
  if (isError || !data) return <p className="text-sm text-brand">Failed to load.</p>;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-ink">{data.subscriber_name}</h1>
            <TriageBadge triage={data.triage} source={data.triage_source} />
            <span className="text-xs text-ink/50">{data.status}</span>
          </div>
          <p className="text-sm text-ink/60">
            {data.area ?? "Unknown area"} · {data.channel} · {dateOnly(data.created_at)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => nav("/complaints")}
          className="text-sm text-ink/70 hover:text-ink"
        >
          ← Back
        </button>
      </div>

      <Section title="Complaint">
        <p className="text-sm text-ink whitespace-pre-wrap">{data.text}</p>
      </Section>

      <Section title="AI triage">
        {data.triage === "PENDING" ? (
          <div className="space-y-3">
            <p className="text-sm text-ink/60">
              Triage hasn't been run. The AI will classify routine ops; sensitive
              cases (billing, disputes, abuse) are always escalated to a human by
              the rules engine before the model is ever consulted.
            </p>
            {canAct && (
              <button
                disabled={triage.isPending}
                onClick={() => triage.mutate()}
                className="bg-ai text-white text-sm px-3 py-1.5 rounded hover:bg-ai/90 disabled:opacity-60"
              >
                {triage.isPending ? "Triaging…" : "Run triage"}
              </button>
            )}
            {triage.isError && (
              <p className="text-xs text-brand">Triage call failed.</p>
            )}
          </div>
        ) : (
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-ink/60">Decision: </span>
              <span className="font-medium text-ink">{data.triage}</span>
              {data.triage_source && (
                <span
                  className={`ml-2 text-xs px-1.5 py-0.5 rounded border ${
                    data.triage_source === "AI"
                      ? "border-ai/30 text-ai"
                      : "border-zinc-300 text-ink/60"
                  }`}
                >
                  {data.triage_source}
                </span>
              )}
            </div>
            {data.triage_reason && (
              <div className="text-xs text-ink/60">Reason: {data.triage_reason}</div>
            )}
            {data.resolution && (
              <p className="text-ink mt-2 whitespace-pre-wrap">{data.resolution}</p>
            )}
            {data.triage === "ESCALATED" && data.status === "OPEN" && (
              <p className="text-xs text-amber-700 mt-2">
                Awaiting human action. AI did not (and will not) auto-resolve this case.
              </p>
            )}
          </div>
        )}
      </Section>

      {data.status === "OPEN" && (
        <Section title="Resolve manually">
          <textarea
            rows={3}
            value={resolution}
            onChange={(e) => setResolution(e.target.value)}
            placeholder="Describe the resolution sent to the customer…"
            className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ai/40"
          />
          <div className="mt-2">
            <button
              disabled={!resolution.trim() || resolve.isPending}
              onClick={() => resolve.mutate()}
              className="bg-ink text-white text-sm px-3 py-1.5 rounded hover:bg-ink/90 disabled:opacity-50"
            >
              {resolve.isPending ? "Saving…" : "Mark resolved"}
            </button>
            {resolve.isError && (
              <p className="text-xs text-brand mt-1">Could not save resolution.</p>
            )}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4">
      <div className="text-sm font-medium text-ink mb-2">{title}</div>
      {children}
    </div>
  );
}
