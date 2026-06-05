import type { Role } from "@/lib/auth";

export interface UserDetail {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Autonomy {
  triage_ai_enabled: boolean;
  triage_auto_resolve_enabled: boolean;
  ai_draft_enabled: boolean;
  high_churn_always_needs_human: boolean;
  assistant_actions_require_admin: boolean;
  locale: string;
  updated_at: string;
  updated_by_id: number | null;
}

export const ROLES = ["ADMIN", "SALES", "CIRCULATION", "ACCOUNTS"] as const;
