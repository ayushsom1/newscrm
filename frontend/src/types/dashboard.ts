export type Severity = "AUTO" | "APPROVE" | "HUMAN";

export interface KpiBlock {
  label: string;
  value: number;
  hint: string | null;
}

export interface Kpis {
  blocks: KpiBlock[];
  revenue_running_total_inr: string;
}

export interface ExceptionQueueItem {
  type: string;
  ref_id: number;
  severity: Severity;
  summary: string;
  detail: string | null;
  ref_url: string;
}

export interface ExceptionQueue {
  items: ExceptionQueueItem[];
  counts: Record<Severity, number>;
}

export interface Tender {
  id: number;
  title: string;
  department: string;
  deadline: string;
  est_value: string;
  status: "OPEN" | "SUBMITTED" | "WON" | "LOST" | "CLOSED";
  notes: string | null;
  created_at: string;
  updated_at: string;
}
