// 统计/指标函数（与 Python 端 indicators.py 口径一致，Wilder RSI / MA / 连跌 / 回撤）

/** Wilder RSI（period=14） */
export function rsi(closes: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length <= period) return out;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = closes[i] - closes[i - 1];
    if (d > 0) gain += d; else loss -= d;
  }
  let avgG = gain / period, avgL = loss / period;
  out[period] = avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL);
  for (let i = period + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    avgG = (avgG * (period - 1) + Math.max(d, 0)) / period;
    avgL = (avgL * (period - 1) + Math.max(-d, 0)) / period;
    out[i] = avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL);
  }
  return out;
}

export function sma(closes: number[], n: number): (number | null)[] {
  const out: (number | null)[] = new Array(closes.length).fill(null);
  let sum = 0;
  for (let i = 0; i < closes.length; i++) {
    sum += closes[i];
    if (i >= n) sum -= closes[i - n];
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}

/** 连续下跌天数（当日收跌 +1，否则清零） */
export function downStreak(closes: number[]): number[] {
  const out: number[] = [];
  let run = 0;
  for (let i = 0; i < closes.length; i++) {
    run = i > 0 && closes[i] < closes[i - 1] ? run + 1 : 0;
    out.push(run);
  }
  return out;
}

/** 滚动窗口内最大回撤（%，dd<=0） */
export function rollingDrawdown(closes: number[], window: number): (number | null)[] {
  const out: (number | null)[] = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    const start = Math.max(0, i - window + 1);
    let peak = -Infinity;
    for (let j = start; j <= i; j++) peak = Math.max(peak, closes[j]);
    out[i] = (closes[i] - peak) / peak * 100;
  }
  return out;
}

/** 数组百分位：当前值在过去 lookback 个样本（含当日）中的分位 0-100 */
export function percentile(values: number[], lookback: number): number | null {
  if (values.length === 0) return null;
  const cur = values[values.length - 1];
  const w = values.slice(Math.max(0, values.length - lookback));
  const le = w.filter((v) => v <= cur).length;
  return le / w.length * 100;
}

export interface YearStat {
  year: number;
  ret: number | null;       // 年度收益 %
  maxDrawdown: number | null; // 年内最大回撤 %（负值）
  end: number;
}

/** 逐年收益 + 年内最大回撤（峰谷均取年内数据） */
export function yearlyStats(points: [string, number][]): YearStat[] {
  const byYear = new Map<number, { start: number; end: number; peak: number; maxDd: number }>();
  for (const [d, v] of points) {
    const y = Number(d.slice(0, 4));
    let s = byYear.get(y);
    if (!s) {
      s = { start: v, end: v, peak: v, maxDd: 0 };
      byYear.set(y, s);
    }
    s.end = v;
    s.peak = Math.max(s.peak, v);
    s.maxDd = Math.min(s.maxDd, (v - s.peak) / s.peak * 100);
  }
  return [...byYear.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([year, s]) => ({
      year,
      ret: s.start > 0 ? (s.end - s.start) / s.start * 100 : null,
      maxDrawdown: s.maxDd,
      end: s.end,
    }));
}

/** 连跌 k 天结束后，后 h 日收益统计（用于连跌统计表） */
export function streakForwardStats(
  closes: number[], k: number, h: number,
): { count: number; winRate: number; avg: number } {
  const rets: number[] = [];
  let run = 0;
  for (let i = 0; i < closes.length; i++) {
    run = i > 0 && closes[i] < closes[i - 1] ? run + 1 : 0;
    if (run === k && i + h < closes.length) {
      rets.push((closes[i + h] - closes[i]) / closes[i] * 100);
    }
  }
  if (rets.length === 0) return { count: 0, winRate: 0, avg: 0 };
  return {
    count: rets.length,
    winRate: rets.filter((r) => r > 0).length / rets.length * 100,
    avg: rets.reduce((a, b) => a + b, 0) / rets.length,
  };
}

/** 两条序列从共同起点归一化为 1 的对比曲线 */
export function normalizePair(
  a: [string, number][], b: [string, number][],
): { dates: string[]; a: number[]; b: number[] } {
  const mapB = new Map(b);
  const common = a.filter(([d]) => mapB.has(d));
  if (common.length === 0) return { dates: [], a: [], b: [] };
  const [d0, a0] = common[0];
  const b0 = mapB.get(d0)!;
  const dates: string[] = [], av: number[] = [], bv: number[] = [];
  for (const [d, v] of common) {
    dates.push(d);
    av.push(v / a0);
    bv.push(mapB.get(d)! / b0);
  }
  return { dates, a: av, b: bv };
}
