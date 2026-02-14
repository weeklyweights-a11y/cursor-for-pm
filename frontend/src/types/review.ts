export interface ReviewQueueItem {
  id: string;
  org_id: string;
  feedback_item_id: string;
  source_domain: string;
  source_company_name: string | null;
  candidate_customer_id: string | null;
  candidate_customer_name: string | null;
  candidate_domain: string | null;
  confidence: number | null;
  status: string;
  created_at: string;
}
