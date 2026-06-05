export type ClassifiedStatus = "QUOTED" | "PAID" | "PUBLISHED" | "CANCELLED";
export type Locale = "IN" | "NP";

export interface Quote {
  currency: string;
  tax_label: string;
  word_count: number;
  net: string;
  tax: string;
  total: string;
  breakdown: Record<string, string>;
}

export interface Classified {
  id: number;
  customer_name: string;
  customer_phone: string;
  text: string;
  word_count: number;
  category: string;
  duration_days: number;
  locale: string;
  currency: string;
  price_net: string;
  price_tax: string;
  price_total: string;
  status: ClassifiedStatus;
  publish_date: string | null;
  created_at: string;
  paid_at: string | null;
  published_at: string | null;
}

export const CATEGORIES = [
  "GENERAL",
  "MATRIMONIAL",
  "PROPERTY",
  "JOBS",
  "OBITUARY",
  "VEHICLES",
] as const;
