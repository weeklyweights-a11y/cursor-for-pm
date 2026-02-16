export interface SpecSection {
  key: string;
  title: string;
  content: string;
  generated_at?: string;
  edited?: boolean;
  edit_history?: Array<{ content?: string; at?: string }>;
}

export interface Spec {
  id: string;
  brief_id: string;
  theme_id: string;
  version: number;
  status: string;
  title: string;
  scope: string;
  target_audience: string;
  sections: SpecSection[];
  config?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface SpecStatus {
  spec_id: string;
  status: string;
  sections_completed: number;
  sections_total: number;
  current_section: string | null;
}

export interface GenerateSpecRequest {
  brief_id: string;
  scope: string;
  target_audience: string;
  custom_instructions?: string | null;
}

export interface SpecExportResponse {
  markdown_content: string;
  filename: string;
  format: string;
}
