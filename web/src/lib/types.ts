// 与 scripts/export_web_data.py 输出的 JSON 结构一一对应
export type FundKind = "etf" | "lof" | "otc";

export interface FundMeta {
  name: string;
  kind: FundKind;
  market: string | null;
  index_name: string;
  share: string;
}

export interface FundCard {
  score: number | null;
  rating: string;
  nav: number | null;
  nav_date: string;
  pct: number | null;
  rsi: number | null;
  dd60: number | null;
  dev60: number | null;
  pe_pct: number | null;
  premium_now: number | null;
  premium_close: number | null;
  premium_veto: boolean;
}

export interface FundLimitsInfo {
  status_buy: string | null;
  daily_limit: number | null;
  min_buy: number | null;
  subscribe_rate: number | null;
}

export interface SummaryFund extends FundMeta {
  card: FundCard | null;
  limits: FundLimitsInfo | null;
}

export interface Temperature {
  temp: number | null;
  level: string;
  premium_median: number | null;
  premium_score: number | null;
  crowd_ratio: number | null;
  crowd_score: number | null;
  n_market: number;
  n_otc: number;
}

export interface Summary {
  generated_at: string;
  temperature: Temperature;
  funds: Record<string, SummaryFund>;
}

export interface LimitsFund {
  code: string;
  name: string;
  share: string;
  index_name: string;
  status_buy: string | null;
  status_redeem: string | null;
  daily_limit: number | null;
  min_buy: number | null;
  subscribe_rate: number | null;
  discount: number | null;
  can_buy: boolean | null;
}

export interface LimitEvent {
  date: string;
  code: string;
  name: string;
  field: string;
  from: string | number | null;
  to: string | number | null;
}

export interface Limits {
  updated_at: string;
  funds: LimitsFund[];
  events: LimitEvent[];
}

export type Point2 = [string, number];              // [date, value]
export type Point3 = [string, number, number];      // [date, close, nav]
export type Point4 = [string, number, number, number]; // [date, close, nav, prem%]

export interface IndexData {
  name: string;
  since: number;
  note?: string;
  points: Point2[];
}
