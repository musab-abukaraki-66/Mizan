export type Lang = "ar" | "en";
export type ModelId = "naive" | "seasonal_naive" | "drift" | "ets" | "sarima";
export type Horizon = 1 | 3 | 6;
export const HORIZONS: Horizon[] = [1, 3, 6];
export const MODEL_IDS: ModelId[] = ["naive", "seasonal_naive", "drift", "ets", "sarima"];
export type WindowId = "dev" | "test" | "all";

export interface Validation {
  passed: number;
  warnings: number;
  failed: number;
  total: number;
  ok: boolean;
}
export interface Latest {
  period: string;
  cpi: number;
  mom: number;
  yoy: number;
  yoy_prev: number;
  prev_period: string;
  avg_to_date: number | null;
  avg_to_date_months: number;
  cpi_12m_ago: number;
  validation: Validation;
}
export interface SeriesRow {
  period: string;
  cpi: number;
  mom: number | null;
  yoy: number | null;
}
export interface SeriesPayload {
  rows: SeriesRow[];
  latest: Latest;
}
export interface DmResult {
  stat: number;
  p_value: number;
  n: number;
}
export interface Metrics {
  n: number;
  mae?: number;
  rmse?: number;
  mase?: number;
  mape_pct?: number;
  bias?: number;
  yoy_mae_pp?: number | null;
  yoy_rmse_pp?: number | null;
  coverage80?: number;
  coverage95?: number;
  width80?: number;
  width95?: number;
  cal_n?: number;
  cal_coverage80?: number;
  cal_coverage95?: number;
  cal_width80?: number;
  cal_width95?: number;
  dm_vs_naive?: DmResult | null;
}
export interface Champion {
  model: ModelId;
  dev_rmse: number;
  naive_dev_rmse: number;
  best_baseline: ModelId;
  best_baseline_dev_rmse: number;
  improvement_vs_naive_pct: number | null;
  improvement_vs_best_baseline_pct: number | null;
  dm_p_vs_naive: number | null;
  test_rmse: number | null;
  naive_test_rmse: number | null;
  beats_naive_on_test: boolean;
  statistical_model_wins_dev: boolean;
}
export interface Band {
  lower: number[];
  upper: number[];
}
export interface ForecastPayload {
  model: ModelId;
  spec: string;
  as_of: string;
  horizon: Horizon;
  periods: string[];
  mean: number[];
  yoy: number[];
  bands: Record<string, Band>;
  yoy_bands: Record<string, Band>;
  interval_method: "calibrated" | "model";
  evaluation: Record<WindowId, Metrics>;
  baseline_evaluation: Record<WindowId, Metrics>;
  champion: Champion;
  is_champion: boolean;
}
export interface OverviewForecast {
  model: ModelId;
  period: string;
  point: number;
  yoy: number;
  lower: number | null;
  upper: number | null;
  yoy_lower: number | null;
  yoy_upper: number | null;
  interval_method: string;
  champion: Champion;
}
export interface Design {
  first_origin: string;
  origins: number;
  test_window: [string, string];
  dev_window: [string, string];
  origins_by_horizon: Record<string, { dev: number; test: number }>;
  mase_scale: number;
}
export interface Overview {
  latest: Latest;
  forecast_summary: Record<string, OverviewForecast>;
  design: Design;
  results_fresh: boolean;
}
export interface ModelInfo {
  id: ModelId;
  name: string;
  description: string;
  baseline: boolean;
}
export interface Arena {
  models: ModelInfo[];
  accuracy: Record<ModelId, Record<string, Record<WindowId, Metrics>>>;
  champions: Record<string, Champion>;
  fit_failures: Record<string, { count: number; examples: { origin: string; reason: string }[] }>;
  selected_specs: Record<string, Record<string, number>>;
  comparison_sample: { rule: string; rows_before: number; rows_after: number };
  design: Design;
  config: { min_train: number; test_months: number; reselect_every: number; horizons: number[]; levels: number[] };
  as_of: string;
}
export interface BacktestSeries {
  origin: string[];
  target: string[];
  window: string[];
  actual: number[];
  forecast: number[];
  lo80: (number | null)[];
  hi80: (number | null)[];
  lo95: (number | null)[];
  hi95: (number | null)[];
  lo80c: (number | null)[];
  hi80c: (number | null)[];
  lo95c: (number | null)[];
  hi95c: (number | null)[];
}
export interface BacktestPayload {
  model: ModelId;
  horizon: Horizon;
  series: BacktestSeries;
  metrics: Record<WindowId, Metrics>;
  test_window: [string, string];
}
export interface Check {
  id: string;
  label: string;
  status: "pass" | "warn" | "fail";
  detail: string;
}
export interface FileRecord {
  year: number;
  url: string;
  bytes: number;
  sha256: string;
  http_last_modified: string | null;
  months_found: number;
  notes: string[];
  average_check: { checked: boolean; ok: boolean | null; abs_diff?: number };
}
export interface Quality {
  source: { publisher: string; publisher_ar: string; dataset: string; landing_page: string; terms_url: string };
  retrieval: { retrieved_at_utc: string; command: string; files: FileRecord[] };
  series: {
    name: string;
    definition: string;
    frequency: string;
    base: string;
    units: string;
    seasonal_adjustment: string;
    geography: string;
    rows: number;
    first_period: string;
    last_period: string;
    missing_periods: string[];
    csv: string;
    csv_sha256: string;
    transformations: string[];
  };
  license: { dos: string; imf: string };
  ingest_validation: { summary: Validation; checks: Check[] };
  crosschecks: {
    imf?: {
      overlap_months?: number;
      mismatched_months?: { period: string; dos: number; imf: number; diff: number }[];
      imf_last?: string;
    };
    press_release?: {
      source: { name: string; url: string };
      reference_month: string;
      ok: boolean;
      results: { id: string; text: string; stated: number; computed: number; ok: boolean }[];
    };
    rebase?: {
      note: string;
      jan_2018_mom_pct_2018base: number;
      jan_2018_mom_pct_2010base: number;
    };
  };
  live_validation: { summary: Validation; checks: Check[] };
  results_fresh: boolean;
  dictionary: { field: string; type: string; description: string }[];
  cache_key: string | null;
  results_generated_at_utc: string | null;
  environment: Record<string, string> | null;
}
export interface Meta {
  publisher: string;
  publisher_ar: string;
  dataset: string;
  landing_page: string;
  retrieved_at_utc: string;
  latest: Latest;
  results_fresh: boolean;
  provenance_verified: boolean;
}
