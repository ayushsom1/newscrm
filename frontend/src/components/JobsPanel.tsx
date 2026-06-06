import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { JobList, JobRun } from "@/types/job";
import { useAuth } from "@/lib/auth";
import { showSuccess } from "@/lib/toast";

const STATUS_STYLES: Record<JobRun["status"], string> = {
  SUCCESS: "bg-green-50 text-green-800 border-green-200",
  FAILED: "bg-red-50 text-brand border-red-200",
  SKIPPED: "bg-zinc-100 text-ink/60 border-zinc-200",
};

const PRETTY: Record<string, string> = {
  nightly_churn_recompute: "Nightly churn recompute",
  daily_expire_contracts: "Daily expire contracts",
  daily_renewal_reminders: "Daily renewal reminders",
};

export default function JobsPanel() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const { data, isLoading } = useQuery<JobList>({
    queryKey: ["jobs"],
    queryFn: async () => (await api.get<JobList>("/jobs")).data,
  });

  const trigger = useMutation({
    mutationFn: async (name: string) =>
      (await api.post<JobRun>(`/jobs/${name}/run`)).data,
    onSuccess: async (run) => {
      await qc.invalidateQueries({ queryKey: ["jobs"] });
      await qc.invalidateQueries({ queryKey: ["dashboard", "queue"] });
      await qc.invalidateQueries({ queryKey: ["dashboard", "kpis"] });
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
      showSuccess(
        `Job ${run.job_name} ran — ${run.items_processed} processed, ${run.notifications_sent} sent`,
      );
    },
  });

  return (
    <div className="bg-white border border-zinc-200 rounded-lg">
      <div className="px-4 py-3 border-b border-zinc-200">
        <div className="text-sm font-medium text-ink">Scheduled jobs</div>
        <div className="text-xs text-ink/60">
          The CRM runs while no one is looking. Each job is idempotent per day.
        </div>
      </div>

      <ul className="divide-y divide-zinc-100">
        {isLoading && (
          <li className="px-4 py-6 text-center text-ink/50 text-sm">Loading…</li>
        )}
        {data?.jobs.map((j) => (
          <li key={j.name} className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-medium text-ink">
                  {PRETTY[j.name] ?? j.name}
                </div>
                {j.last_run ? (
                  <div className="text-xs text-ink/60 mt-0.5">
                    Last run {j.last_run.window_date} ·{" "}
                    {j.last_run.items_processed} processed,{" "}
                    {j.last_run.notifications_sent} sent · {j.last_run.triggered_by}
                  </div>
                ) : (
                  <div className="text-xs text-ink/50 mt-0.5">Never run.</div>
                )}
                {j.last_run?.error && (
                  <pre className="mt-2 text-[11px] text-brand whitespace-pre-wrap max-h-32 overflow-auto bg-red-50 border border-red-200 rounded p-2">
                    {j.last_run.error.slice(0, 600)}
                  </pre>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {j.last_run && (
                  <span
                    className={`text-[10px] uppercase font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[j.last_run.status]}`}
                  >
                    {j.last_run.status}
                  </span>
                )}
                {isAdmin && (
                  <button
                    disabled={trigger.isPending}
                    onClick={() => trigger.mutate(j.name)}
                    className="text-xs bg-nav text-white px-2.5 py-1 rounded hover:bg-nav-darker disabled:opacity-60"
                  >
                    {trigger.isPending && trigger.variables === j.name
                      ? "Running…"
                      : "Run now"}
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
