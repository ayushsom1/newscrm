export type AdvertiserStatus = "ACTIVE" | "INACTIVE" | "PROSPECT";
export type ContractStatus = "ACTIVE" | "EXPIRED" | "CANCELLED";
export type ChurnBand = "low" | "med" | "high";

export interface Churn {
  score: number | null;
  band: ChurnBand | null;
  reasons: string[];
  updated_at: string | null;
}

export interface Advertiser {
  id: number;
  name: string;
  category: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  annual_value: string;
  spend_trend: string;
  proposal_open_rate: string;
  status: AdvertiserStatus;
  created_at: string;
  updated_at: string;
  churn: Churn;
}

export interface Contract {
  id: number;
  advertiser_id: number;
  start_date: string;
  end_date: string;
  value: string;
  slots: number;
  status: ContractStatus;
  created_at: string;
}

export interface AdvertiserDetail extends Advertiser {
  contracts: Contract[];
}
