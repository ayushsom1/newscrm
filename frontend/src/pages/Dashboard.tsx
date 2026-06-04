const CARDS = [
  { label: "Advertisers", value: "—", hint: "CRUD in Sprint 2" },
  { label: "At-risk renewals", value: "—", hint: "Engine in Sprint 4" },
  { label: "Open complaints", value: "—", hint: "AI triage in Sprint 5" },
  { label: "Pending approvals", value: "—", hint: "Approval flow in Sprint 6" },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Dashboard</h1>
        <p className="text-sm text-ink/60">
          KPIs and the exception queue land here. Skeleton only for now.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {CARDS.map((c) => (
          <div
            key={c.label}
            className="bg-white border border-zinc-200 rounded-lg p-4"
          >
            <div className="text-xs text-ink/60">{c.label}</div>
            <div className="mt-1 text-2xl font-semibold text-ink">{c.value}</div>
            <div className="mt-2 text-xs text-ink/50">{c.hint}</div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg p-6">
        <div className="text-sm font-medium text-ink">Exception queue</div>
        <div className="mt-2 text-sm text-ink/60">
          The human-on-the-loop surface — items will appear here as features land.
        </div>
      </div>
    </div>
  );
}
