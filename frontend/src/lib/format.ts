export function money(n: number | string | null | undefined, currency = "INR"): string {
  if (n === null || n === undefined || n === "") return "—";
  const num = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export function pct(n: number | string | null | undefined): string {
  if (n === null || n === undefined || n === "") return "—";
  const num = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(num)) return "—";
  return `${num.toFixed(1)}%`;
}

export function dateOnly(s: string | null | undefined): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-IN");
}
