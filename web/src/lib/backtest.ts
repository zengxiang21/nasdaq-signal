// 胜率回测引擎（与 Python backtest.py 同口径，前端实时调参计算）
import { downStreak, rsi, sma } from "./stats";

export type RuleKind =
  | "any"        // 基准：任意一天
  | "weekday"    // 星期几买入
  | "streak"     // 连跌 ≥ N 天
  | "drop"       // 单日跌 ≥ X%
  | "belowMa"    // 低于 MA20 超 X%
  | "rsiBelow"   // RSI < N
  | "drawdown"   // 60日回撤 ≥ X%
  | "premiumLe"; // 溢价 ≤ X%（仅场内基金）

export interface RuleSpec {
  kind: RuleKind;
  param: number; // weekday: 0-4；其余为阈值
}

export interface HorizonStat {
  n: number;
  winRate: number | null;
  avg: number | null;
  median: number | null;
  profitFactor: number | null;
}

export const HORIZONS = [1, 3, 5, 10, 20, 60];

/** pts: [date, close, ...]，第三个元素存在且 premiumRule=true 时可用溢价规则 */
export function runBacktest(
  pts: [string, number][],
  rule: RuleSpec,
  horizons: number[] = HORIZONS,
  premiumSeries?: (number | null)[],
): Record<number, HorizonStat> {
  const closes = pts.map((p) => p[1]);
  const n = closes.length;
  const mask = new Array<boolean>(n).fill(false);
  switch (rule.kind) {
    case "any":
      mask.fill(true);
      break;
    case "weekday": {
      for (let i = 0; i < n; i++)
        mask[i] = new Date(pts[i][0] + "T00:00:00").getDay() === rule.param;
      break;
    }
    case "streak": {
      const st = downStreak(closes);
      for (let i = 0; i < n; i++) mask[i] = st[i] >= rule.param;
      break;
    }
    case "drop": {
      for (let i = 1; i < n; i++)
        mask[i] = (closes[i] - closes[i - 1]) / closes[i - 1] * 100 <= -rule.param;
      break;
    }
    case "belowMa": {
      const ma = sma(closes, 20);
      for (let i = 0; i < n; i++)
        mask[i] = ma[i] != null && (closes[i] - ma[i]!) / ma[i]! * 100 <= -rule.param;
      break;
    }
    case "rsiBelow": {
      const rv = rsi(closes, 14);
      for (let i = 0; i < n; i++) mask[i] = rv[i] != null && rv[i]! < rule.param;
      break;
    }
    case "drawdown": {
      // 60 日滚动回撤
      for (let i = 0; i < n; i++) {
        const start = Math.max(0, i - 59);
        let peak = -Infinity;
        for (let j = start; j <= i; j++) peak = Math.max(peak, closes[j]);
        mask[i] = (closes[i] - peak) / peak * 100 <= -rule.param;
      }
      break;
    }
    case "premiumLe": {
      if (!premiumSeries) break;
      for (let i = 0; i < n; i++)
        mask[i] = premiumSeries[i] != null && premiumSeries[i]! <= rule.param;
      break;
    }
  }

  const out: Record<number, HorizonStat> = {};
  for (const h of horizons) {
    const rets: number[] = [];
    for (let i = 0; i < n; i++) {
      if (mask[i] && i + h < n)
        rets.push((closes[i + h] - closes[i]) / closes[i] * 100);
    }
    if (rets.length === 0) {
      out[h] = { n: 0, winRate: null, avg: null, median: null, profitFactor: null };
      continue;
    }
    const wins = rets.filter((r) => r > 0);
    const losses = rets.filter((r) => r <= 0);
    const avgLoss = losses.length ? losses.reduce((a, b) => a + b, 0) / losses.length : 0;
    const sorted = [...rets].sort((a, b) => a - b);
    const median = sorted.length % 2
      ? sorted[(sorted.length - 1) / 2]
      : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
    const avgWin = wins.length ? wins.reduce((a, b) => a + b, 0) / wins.length : 0;
    out[h] = {
      n: rets.length,
      winRate: wins.length / rets.length * 100,
      avg: rets.reduce((a, b) => a + b, 0) / rets.length,
      median,
      profitFactor: avgLoss < 0 && wins.length ? avgWin / Math.abs(avgLoss) : null,
    };
  }
  return out;
}
