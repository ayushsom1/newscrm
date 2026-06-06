import { Fragment } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";

interface Crumb {
  label: string;
  to?: string;
}

interface AdvertiserShape {
  name?: string;
}
interface SubscriberShape {
  name?: string;
}
interface ComplaintShape {
  subscriber_name?: string;
}

const NUMERIC = /^\d+$/;

function computeCrumbs(pathname: string, qc: ReturnType<typeof useQueryClient>): Crumb[] {
  if (pathname === "/") return [{ label: "Dashboard" }];
  const parts = pathname.split("/").filter(Boolean);
  const [top, second, third] = parts;

  if (top === "advertisers") {
    const out: Crumb[] = [
      { label: "Advertisers", to: second ? "/advertisers" : undefined },
    ];
    if (second === "new") {
      out.push({ label: "New advertiser" });
    } else if (second && NUMERIC.test(second)) {
      const adv = qc.getQueryData<AdvertiserShape>(["advertiser", second]);
      const label = adv?.name ?? `#${second}`;
      out.push({ label, to: third ? `/advertisers/${second}` : undefined });
      if (third === "edit") out.push({ label: "Edit" });
    }
    return out;
  }

  if (top === "classifieds") {
    const out: Crumb[] = [
      { label: "Classifieds", to: second ? "/classifieds" : undefined },
    ];
    if (second === "new") out.push({ label: "New classified" });
    return out;
  }

  if (top === "subscribers") {
    const out: Crumb[] = [
      { label: "Subscribers", to: second ? "/subscribers" : undefined },
    ];
    if (second === "new") {
      out.push({ label: "New subscriber" });
    } else if (second === "forecast") {
      out.push({ label: "Print-run forecast" });
    } else if (second && NUMERIC.test(second)) {
      const sub = qc.getQueryData<SubscriberShape>(["subscriber", second]);
      const label = sub?.name ?? `#${second}`;
      out.push({ label, to: third ? `/subscribers/${second}` : undefined });
      if (third === "edit") out.push({ label: "Edit" });
    }
    return out;
  }

  if (top === "complaints") {
    const out: Crumb[] = [
      { label: "Complaints", to: second ? "/complaints" : undefined },
    ];
    if (second === "new") {
      out.push({ label: "New complaint" });
    } else if (second && NUMERIC.test(second)) {
      const c = qc.getQueryData<ComplaintShape>(["complaint", second]);
      out.push({ label: c?.subscriber_name ?? `#${second}` });
    }
    return out;
  }

  if (top === "assistant") return [{ label: "Assistant" }];
  if (top === "settings") return [{ label: "Settings" }];

  return [
    { label: top ? top.charAt(0).toUpperCase() + top.slice(1) : "Home" },
  ];
}

export default function Breadcrumb() {
  const { pathname } = useLocation();
  const qc = useQueryClient();
  const crumbs = computeCrumbs(pathname, qc);

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center text-sm text-ink/60 min-w-0"
    >
      {crumbs.map((c, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <Fragment key={`${c.label}-${i}`}>
            {i > 0 && (
              <ChevronRight
                size={14}
                className="text-ink/30 mx-1.5 shrink-0"
                aria-hidden="true"
              />
            )}
            {c.to && !isLast ? (
              <Link
                to={c.to}
                className="hover:text-ink transition-colors truncate max-w-[18rem] focus-visible:ring-2 focus-visible:ring-ai/40 outline-none rounded"
              >
                {c.label}
              </Link>
            ) : (
              <span className="text-ink font-medium truncate max-w-[24rem]">
                {c.label}
              </span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
