export type ProposalSource = "AI_DRAFT" | "HUMAN";
export type ProposalStatus = "DRAFT" | "APPROVED" | "SENT" | "REJECTED";

export interface Proposal {
  id: number;
  advertiser_id: number;
  subject: string;
  body: string;
  source: ProposalSource;
  status: ProposalStatus;
  needs_human: boolean;
  needs_human_reason: string | null;
  model_used: string | null;
  created_by_id: number | null;
  approved_by_id: number | null;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
  sent_at: string | null;
}
