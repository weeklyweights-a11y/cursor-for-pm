export interface CustomerUploadResult {
  created: number;
  updated: number;
  skipped: number;
  items_queued?: number;
}

export interface Customer {
  id: string;
  org_id: string;
  domain: string;
  company_name: string | null;
  segment: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TopCustomer {
  id: string;
  domain: string;
  company_name: string | null;
  feedback_count: number;
}

export interface CustomerDetail extends Customer {
  feedback_count: number;
  feedback_by_source: Record<string, number>;
  latest_feedback_date: string | null;
}
