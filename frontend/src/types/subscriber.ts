export type Plan = "DAILY" | "WEEKEND" | "SUNDAY_ONLY";
export type SubscriberStatus = "ACTIVE" | "PAUSED" | "CANCELLED";
export type SubscriptionStatus = "ACTIVE" | "EXPIRED" | "CANCELLED";
export type Severity = "low" | "med" | "high";

export interface Renewal {
  at_risk: boolean;
  severity: Severity;
  reasons: string[];
  days_to_renew: number | null;
}

export interface Subscriber {
  id: number;
  name: string;
  phone: string;
  area: string;
  address: string | null;
  plan: Plan;
  status: SubscriberStatus;
  missed_payments: number;
  created_at: string;
  updated_at: string;
  renewal: Renewal;
}

export interface Subscription {
  id: number;
  subscriber_id: number;
  plan: Plan;
  start_date: string;
  renew_date: string;
  monthly_price: string;
  status: SubscriptionStatus;
  created_at: string;
}

export interface SubscriberDetail extends Subscriber {
  subscriptions: Subscription[];
}

export interface AreaForecast {
  area: string;
  active_subs: number;
  newsstand_buffer: number;
  returns_pct: number;
  target: number;
}

export interface ForecastSummary {
  total_target: number;
  total_active: number;
  areas: AreaForecast[];
}

export const PLANS: Plan[] = ["DAILY", "WEEKEND", "SUNDAY_ONLY"];
