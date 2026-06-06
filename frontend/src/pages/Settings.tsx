import { useState } from "react";
import UsersPanel from "@/components/UsersPanel";
import AutonomyPanel from "@/components/AutonomyPanel";

type Tab = "users" | "autonomy";

export default function Settings() {
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="space-y-6">
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
                ? "border-nav text-nav"
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
