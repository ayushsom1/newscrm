import { useState } from "react";
import UsersPanel from "@/components/UsersPanel";
import AutonomyPanel from "@/components/AutonomyPanel";

type Tab = "users" | "autonomy";

export default function Settings() {
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Settings</h1>
        <p className="text-sm text-ink/60">
          User management and the AI autonomy dial — what the assistant may do
          by itself vs. what needs a human to approve.
        </p>
      </div>

      <div className="flex gap-1 border-b border-zinc-200">
        {(
          [
            ["users", "Users & roles"],
            ["autonomy", "Autonomy dial"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`text-sm px-3 py-2 -mb-px border-b-2 ${
              tab === id
                ? "border-ink text-ink"
                : "border-transparent text-ink/60 hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "users" && <UsersPanel />}
      {tab === "autonomy" && <AutonomyPanel />}
    </div>
  );
}
