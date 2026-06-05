export type ComplaintChannel = "PHONE" | "EMAIL" | "WHATSAPP" | "WALK_IN";
export type ComplaintTriage = "PENDING" | "AUTO" | "ESCALATED";
export type ComplaintStatus = "OPEN" | "RESOLVED" | "CANCELLED";

export interface Complaint {
  id: number;
  subscriber_name: string;
  subscriber_phone: string | null;
  area: string | null;
  text: string;
  channel: ComplaintChannel;
  triage: ComplaintTriage;
  triage_reason: string | null;
  triage_source: string | null;
  resolution: string | null;
  status: ComplaintStatus;
  assigned_to_id: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface TriageResponse {
  auto: boolean;
  resolution: string;
  source: "AI" | "ENGINE";
  reason: string;
}
