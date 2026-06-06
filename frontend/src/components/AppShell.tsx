import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Building2,
  ChevronsLeft,
  ChevronsRight,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareWarning,
  Newspaper,
  Settings as SettingsIcon,
  Sparkles,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import Breadcrumb from "@/components/Breadcrumb";
import { useAuth } from "@/lib/auth";
import { useLocale } from "@/lib/locale";
import { useSidebarState } from "@/lib/useSidebarState";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/advertisers", label: "Advertisers", icon: Building2 },
  { to: "/classifieds", label: "Classifieds", icon: Newspaper },
  { to: "/subscribers", label: "Subscribers", icon: Users },
  { to: "/complaints", label: "Complaints", icon: MessageSquareWarning },
  { to: "/assistant", label: "Assistant", icon: Sparkles },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { locale, currency } = useLocale();
  const { collapsed, toggle } = useSidebarState();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Auto-close mobile drawer on navigation.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Lock body scroll while drawer open.
  useEffect(() => {
    if (mobileOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [mobileOpen]);

  // On desktop the sidebar width follows the collapsed flag; on mobile it
  // doesn't matter (drawer overlay).
  const desktopWidth = collapsed ? "md:w-16" : "md:w-60";

  return (
    <div className="h-screen flex font-sans bg-zinc-50 text-ink overflow-hidden">
      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-nav/40 md:hidden"
        />
      )}

      <aside
        className={[
          "bg-nav text-white flex flex-col border-r border-black/30 shrink-0",
          "transition-[width,transform] duration-200 ease-out",
          // Mobile: fixed slide-in drawer at 240px
          "fixed inset-y-0 left-0 z-40 w-60",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          // Desktop: in-flow, no slide, width responds to collapsed
          "md:static md:translate-x-0",
          desktopWidth,
        ].join(" ")}
        aria-label="Primary navigation"
      >
        {/* Brand */}
        <div className="h-16 flex items-center border-b border-white/10 px-3">
          {collapsed ? (
            <>
              {/* Compact mark — desktop collapsed */}
              <div
                className="hidden md:flex w-9 h-9 mx-auto rounded bg-brand/20 items-center justify-center"
                title="News CRM"
              >
                <span className="text-brand font-bold text-xs tracking-wide">
                  NC
                </span>
              </div>
              {/* Full mark — mobile drawer (where "collapsed" is irrelevant) */}
              <div className="flex md:hidden items-center gap-2.5 px-1 flex-1">
                <div className="w-9 h-9 rounded bg-brand/20 flex items-center justify-center shrink-0">
                  <span className="text-brand font-bold text-xs tracking-wide">
                    NC
                  </span>
                </div>
                <div className="min-w-0 leading-tight">
                  <div className="text-sm font-semibold text-white">News CRM</div>
                  <div className="text-[10px] text-white/50">
                    human-on-the-loop
                  </div>
                </div>
              </div>
              {/* Mobile close button */}
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="md:hidden text-white/60 hover:text-white p-1.5"
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2.5 px-1 flex-1">
                <div className="w-9 h-9 rounded bg-brand/20 flex items-center justify-center shrink-0">
                  <span className="text-brand font-bold text-xs tracking-wide">
                    NC
                  </span>
                </div>
                <div className="min-w-0 leading-tight">
                  <div className="text-sm font-semibold text-white">News CRM</div>
                  <div className="text-[10px] text-white/50">
                    human-on-the-loop
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="md:hidden text-white/60 hover:text-white p-1.5"
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {NAV.map((n) => {
            // On mobile the nav is full-width (labels always visible). The
            // `collapsed` shape only applies at md and up.
            const desktopCollapsed = collapsed;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                title={desktopCollapsed ? n.label : undefined}
                className={({ isActive }) =>
                  [
                    "group relative flex items-center gap-3 rounded text-sm outline-none",
                    "focus-visible:ring-2 focus-visible:ring-brand",
                    "transition-colors",
                    desktopCollapsed
                      ? "px-3 py-2 md:justify-center md:px-0 md:py-2.5"
                      : "px-3 py-2",
                    isActive
                      ? "bg-white/10 text-white"
                      : "text-white/70 hover:bg-white/5 hover:text-white",
                  ].join(" ")
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span
                        className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-brand"
                        aria-hidden="true"
                      />
                    )}
                    <n.icon size={18} strokeWidth={1.75} className="shrink-0" />
                    <span
                      className={
                        desktopCollapsed
                          ? "inline md:hidden truncate"
                          : "truncate"
                      }
                    >
                      {n.label}
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Collapse toggle — desktop only */}
        <div className="border-t border-white/10 p-2 hidden md:block">
          <button
            type="button"
            onClick={toggle}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={`w-full flex items-center py-1.5 rounded text-xs text-white/50 hover:bg-white/5 hover:text-white focus-visible:ring-2 focus-visible:ring-brand outline-none transition-colors ${
              collapsed ? "justify-center" : "justify-between px-2"
            }`}
          >
            {!collapsed && <span>v0.1.0</span>}
            {collapsed ? (
              <ChevronsRight size={16} />
            ) : (
              <ChevronsLeft size={16} />
            )}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <header className="h-16 shrink-0 bg-white border-b border-zinc-200 flex items-center justify-between gap-2 sm:gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-2 -ml-2 rounded text-ink/70 hover:bg-zinc-50 focus-visible:ring-2 focus-visible:ring-ai/40 outline-none"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0 flex-1">
              <Breadcrumb />
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <div
              className="hidden sm:block text-[10px] uppercase tracking-wider font-medium px-2 py-1 rounded border border-zinc-200 text-ink/60"
              title={`Locale ${locale} — currency ${currency}`}
            >
              {locale} · {currency}
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              <div className="text-sm leading-tight text-right hidden lg:block">
                <div className="text-ink font-medium">{user?.name}</div>
                <div className="text-[10px] uppercase tracking-wide text-ink/50">
                  {user?.role}
                </div>
              </div>
              <div
                className="w-9 h-9 rounded-full bg-nav/5 border border-zinc-200 flex items-center justify-center text-xs font-semibold text-ink/70"
                title={user?.name}
              >
                {initials(user?.name)}
              </div>
              <button
                type="button"
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                className="p-2 rounded text-ink/60 hover:text-brand hover:bg-zinc-50 focus-visible:ring-2 focus-visible:ring-brand outline-none transition-colors"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 min-h-0 overflow-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function initials(name: string | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1]?.[0] ?? "" : "";
  return (first + last).toUpperCase() || "?";
}
