import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export type LocaleCode = "IN" | "NP";

export interface LocaleInfo {
  locale: LocaleCode;
  currency: "INR" | "NPR";
  taxLabel: "GST" | "VAT";
  weeklySpecialDay: "Sunday" | "Saturday";
  // Bound formatters so call sites don't have to know about locale plumbing.
  money: (value: number | string | null | undefined) => string;
  pct: (value: number | string | null | undefined) => string;
}

const DEFAULT: LocaleInfo = makeLocale("IN");

const Ctx = createContext<LocaleInfo>(DEFAULT);

function makeLocale(code: LocaleCode): LocaleInfo {
  const currency = code === "NP" ? "NPR" : "INR";
  const tax = code === "NP" ? "VAT" : "GST";
  const intlLocale = code === "NP" ? "ne-NP" : "en-IN";

  return {
    locale: code,
    currency,
    taxLabel: tax,
    weeklySpecialDay: code === "NP" ? "Saturday" : "Sunday",
    money: (v) => {
      if (v === null || v === undefined || v === "") return "—";
      const n = typeof v === "string" ? Number(v) : v;
      if (Number.isNaN(n)) return "—";
      return new Intl.NumberFormat(intlLocale, {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(n);
    },
    pct: (v) => {
      if (v === null || v === undefined || v === "") return "—";
      const n = typeof v === "string" ? Number(v) : v;
      if (Number.isNaN(n)) return "—";
      return `${n.toFixed(1)}%`;
    },
  };
}

interface AutonomyShape {
  locale: string;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  // Only fetch once authenticated. Endpoint requires a token.
  const q = useQuery<AutonomyShape>({
    queryKey: ["autonomy"],
    queryFn: async () =>
      (await api.get<AutonomyShape>("/settings/autonomy")).data,
    enabled: !!user,
    staleTime: 60_000,
  });

  const code: LocaleCode = q.data?.locale === "NP" ? "NP" : "IN";
  const info = makeLocale(code);
  return <Ctx.Provider value={info}>{children}</Ctx.Provider>;
}

export function useLocale(): LocaleInfo {
  return useContext(Ctx);
}
