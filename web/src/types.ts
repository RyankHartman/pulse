export interface Dataset {
  title: string;
  author: string;
  doi: string;
  url: string;
  license: string;
  file: string;
  bytes: number;
}

export interface Meta {
  generated: string;
  dataset: Dataset;
  titles: { title: string; name: string }[];
}

export interface Check {
  check: string;
  result: string;
  status: "pass" | "warn" | "fail";
  action: string;
}

export interface CalendarDay {
  day: string;
  hours: number;
  frozen: number;
}

export interface Integrity {
  dataset: Dataset;
  summary: {
    rows: number;
    rows_after_dedupe: number;
    rows_clean: number;
    titles: number;
    first_day: string;
    last_day: string;
    snapshots: number;
    expected_snapshots: number;
    never_collected: number;
    frozen_snapshots: number;
    frozen_runs: number;
    usable_snapshots: number;
    raw_coverage_pct: number;
    usable_coverage_pct: number;
    missing_days: string[];
    partial_days: string[];
    nearly_full_days: number;
    duplicate_pairs: number;
    rank_violations: number;
    defect_window: {
      clustered: boolean;
      start: string;
      end: string;
      days: number;
      duplicates: number;
      partial_freezes: number;
      rank_violations: number;
    };
    longest_outage_hours: number;
    long_freezes: { start: string; end: string; hours: number }[];
  };
  outages: { start: string; end: string; hours: number; kind: string }[];
  frozen_example: { title: string; points: { ts: string; ccu: number; frozen: boolean }[] };
  calendar: CalendarDay[];
  checks: Check[];
}

export interface ForecastRow {
  day: string;
  mid: number;
  lo80: number;
  hi80: number;
  lo95: number;
  hi95: number;
  actual?: number | null;
}

export interface ModelRow {
  key: string;
  label: string;
  mape_all: number;
  mape_test: number;
  chosen: boolean;
}

export interface TestStats {
  mape: number;
  naive_mape: number;
  skill_vs_naive: number;
  coverage80: number;
  coverage95: number;
}

export interface TitleForecast {
  title: string;
  name: string;
  series: { day: string; peak: number | null; usable: boolean; hours: number }[];
  imputed_days: number;
  trend: { first28: number; last28: number; change_pct: number };
  holdout: { cutoff: string; model: string; model_label: string; forecast: ForecastRow[] };
  projection: { model: string; model_label: string; forecast: ForecastRow[] };
  backtest: {
    origins: number;
    calibration_origins: number;
    test_origins: number;
    calibration_end: string;
    models: ModelRow[];
    chosen_model: string;
    chosen_label: string;
    test: TestStats & { days_scored: number; picks: Record<string, string> };
    by_horizon: { h: number; model: number; naive: number }[];
  };
  without_cleaning: TestStats;
}

export interface Forecast {
  horizon: number;
  models: Record<string, string>;
  titles: Record<string, TitleForecast>;
}

export interface AnomalyEvent {
  start: string;
  end: string;
  peak_day: string;
  direction: "spike" | "drop";
  days: number;
  z: number;
  actual: number;
  expected: number;
  pct_vs_expected: number;
  platform_share: number;
  class: "title_specific" | "platform_wide" | "data_suspect";
  class_label: string;
  why: string;
}

export interface TitleAnomalies {
  title: string;
  name: string;
  series: { day: string; peak: number | null; expected: number; z: number | null }[];
  events: AnomalyEvent[];
  counts: Record<"title_specific" | "platform_wide" | "data_suspect", number>;
}

export interface Anomalies {
  thresholds: { z: number; min_pct: number; platform_z: number; platform_share: number };
  platform_titles: number;
  titles: Record<string, TitleAnomalies>;
}

export interface KmPoint {
  t: number;
  s: number;
  at_risk: number;
}

export interface CohortStat {
  titles: number;
  exited: number;
  still_ranked: number;
  median_days: number | null;
  survival_day7: number | null;
  survival_day30: number | null;
}

export interface Cohorts {
  definition: { entrant: string; exit: string; breakout: string };
  curves: Record<"all" | "breakout" | "other", KmPoint[]>;
  stats: Record<"all" | "breakout" | "other", CohortStat>;
  scorecard: {
    title: string;
    entered: string;
    last_seen: string;
    days_ranked: number;
    peak_ccu: number;
    day7_index: number | null;
    day30_index: number | null;
    status: string;
  }[];
}

export interface Summary {
  titles: Record<string, { name: string; headline: string; bullets: { label: string; text: string }[] }>;
  next_steps: string[];
}

export interface AppData {
  meta: Meta;
  integrity: Integrity;
  forecast: Forecast;
  anomalies: Anomalies;
  cohorts: Cohorts;
  summary: Summary;
  sql: Record<string, string>;
}
