export interface BriefSection {
  key: string;
  title: string;
  content: string;
  generated_at?: string;
  edited?: boolean;
  edit_history?: Array<{ content?: string; at?: string }>;
}

export interface SolutionEvaluation {
  solution_description: string;
  evaluation: {
    pain_points_addressed?: Array<{ pain_point: string; addressed: boolean; explanation?: string }>;
    coverage_score?: number;
    segment_impact?: Record<string, string>;
    strengths?: string[];
    gaps?: string[];
    recommended_additions?: string[];
    predicted_impact_score?: number;
  };
  evaluated_at?: string;
}

export interface Brief {
  id: string;
  theme_id: string;
  version: number;
  status: string;
  title: string;
  sections: BriefSection[];
  solution_evaluation?: SolutionEvaluation | null;
  metadata?: Record<string, unknown> | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface BriefStatus {
  brief_id: string;
  status: string;
  sections_completed: number;
  sections_total: number;
  current_section: string | null;
}
