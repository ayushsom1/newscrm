import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/advertisers", label: "Advertisers" },
  { to: "/classifieds", label: "Classifieds" },
  { to: "/subscribers", label: "Subscribers" },
  { to: "/complaints", label: "Complaints" },
  { to: "/assistant", label: "Assistant" },
  { to: "/settings", label: "Settings" },
];

export default function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex font-sans bg-zinc-50 text-ink">
      <aside className="w-60 shrink-0 bg-ink text-white flex flex-col">
        <div className="px-5 py-4 border-b border-white/10">
          <div className="text-base font-semibold">News CRM</div>
          <div className="text-xs text-white/50">human-on-the-loop</div>
        </div>
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                `block px-3 py-2 text-sm rounded ${
                  isActive ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 text-xs text-white/40 border-t border-white/10">v0.1.0</div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-zinc-200 flex items-center justify-between px-6">
          <div className="text-sm text-ink/60">Sprint 1 — Auth shell</div>
          <div className="flex items-center gap-3 text-sm">
            <div className="text-ink">
              {user?.name}{" "}
              <span className="text-ink/50">· {user?.role}</span>
            </div>
            <button
              onClick={logout}
              className="text-ink/70 hover:text-brand text-xs underline-offset-2 hover:underline"
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
