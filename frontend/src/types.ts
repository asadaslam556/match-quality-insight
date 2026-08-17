export type AucPair = { rule: number | null; llm: number | null; n: number };

export type QualityGate = {
  status: "pass" | "warn" | "fail" | "skipped";
  baseline_version?: string;
  current_version?: string;
  llm_psi?: number;
  rule_psi_control?: number;
  warn_at?: number;
  fail_at?: number;
  mean_llm_score?: { baseline: number; current: number };
  flag_rate_at_threshold?: { threshold: number; baseline: number; current: number };
};

export type Overview = {
  counts: {
    total_applications: number;
    decided: number;
    pending: number;
    pending_rate: number;
    positive_rate: number;
    hire_rate: number;
    jobs: number;
    candidates: number;
  };
  pooled: AucPair;
  excluding_healthcare: AucPair;
  quality_gate: QualityGate;
};

export type Quadrant = {
  quadrant: string;
  decided: number;
  positives: number;
  positive_rate: number;
};

export type Agreement = {
  excluded_job_family: string | null;
  quadrants: Quadrant[];
  agreement_rate: number | null;
  winner_on_disagreement: string | null;
};

export type CalibrationBand = {
  llm_model_version: string;
  band: number;
  band_label: string;
  decided: number;
  positive_rate: number;
  is_small_sample: boolean;
};

export type MonthlyEngagement = {
  month: string;
  applications: number;
  profile_opened_rate: number;
  ai_score_viewed_rate: number;
  shortlisted_rate: number;
};

export type Funnel = {
  applications: number;
  profile_opened: number;
  ai_score_viewed: number;
  shortlisted: number;
  no_events: number;
  positive_rate_when_shortlisted: number;
  positive_rate_when_not_shortlisted: number;
};

export type Segment = {
  segment: string;
  applications: number;
  decided: number;
  positives: number;
  positive_rate: number | null;
  positive_rate_ci: [number, number] | null;
  mean_rule_score: number;
  mean_llm_score: number;
  low_fit_rate: number;
  good_fit_rate: number;
  rule_auc: number | null;
  llm_auc: number | null;
  is_small_sample: boolean;
};
