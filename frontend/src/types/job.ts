export type JobStatus = "SUCCESS" | "FAILED" | "SKIPPED";

export interface JobRunDetails {
  [k: string]: unknown;
}

export interface JobRun {
  id: number;
  job_name: string;
  window_date: string;
  status: JobStatus;
  items_processed: number;
  notifications_sent: number;
  report: JobRunDetails | null;
  error: string | null;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
}

export interface JobInfo {
  name: string;
  last_run: JobRun | null;
}

export interface JobList {
  jobs: JobInfo[];
}
