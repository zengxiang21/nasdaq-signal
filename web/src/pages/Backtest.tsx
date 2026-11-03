import { useEffect, useMemo, useState } from "react";
import { Card, ErrorBlock, Loading, SectionTitle, TableWrap, Td, Th, fmtPct } from "../components/ui";
import { HORIZONS, runBacktest, type HorizonStat, type RuleKind } from "../lib/backtest";
import { loadIndex, loadNav, loadPremium, loadSummary } from "../lib/data";
import type { Point2, Summary } from "../lib/types";

interface Instrument {
  id: string;
  label: string;
  points: Point2[];          // [date, close]
  premiumMap?: Map<string, number>;
  hasPremium: boolean;
}

const RULES: { kind: RuleKind; label: string; params: { v: number; t: string }[] }[] = [
  { kind: "weekday", label: "星期几买入", params: [0, 1, 2, 3, 4].map((v) => ({ v, t: "周" + "一二三四五"[v] })) },
  { kind: "streak", label: "连跌 ≥ N 天", params: [2, 3, 4, 5].map((v) => ({ v, t: `${v}天` })) },
  { kind: "drop", label: "单日跌 ≥ X%", params: [1, 1.5, 2, 2.5, 3].map((v) => ({ v, t: `${v}%` })) },
  { kind: "belowMa", label: "低于 MA20 超 X%", params: [0, 3, 5, 8].map((v) => ({ v, t: `${v}%` })) },
  { kind: "rsiBelow", label: "RSI < N", params: [25, 30, 35, 40].map((v) => ({ v, t: `${v}` })) },
  { kind: "drawdown", label: "60日回撤 ≥ X%", params: [5, 10, 15, 20].map((v) => ({ v, t: `${v}%` })) },
  { kind: "premiumLe", label: "溢价 ≤ X%（仅场内）", params: [0, 1, 2, 3].map((v) => ({ v, t: `${v}%` })) },
];

function StatCell({ s }: { s: HorizonStat }) {
  if (s.n === 0) return <span className="text-zinc-600">-</span>;
  const small = s.n < 30;
  return (
    <span className={small ? "text-zinc-600" : "text-zinc-200"}
      title={small ? `样本仅 ${s.n} 个，统计意义弱` : undefined}>
      {s.winRate!.toFixed(1)}% <span className="text-[11px] text-zinc-500">/ {s.avg! >= 0 ? "+" : ""}{s.avg!.toFixed(2)}%</span>
      <span className="ml-1 text-[10px] text-zinc-600">n={s.n}</span>
      {s.profitFactor != null && <span className="ml-1 text-[10px] text-zinc-600">盈亏比{s.profitFactor.toFixed(2)}</span>}
    </span>
  );
}

export default function Backtest() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selId, setSelId] = useState("idx-spx");
  const [rule, setRule] = useState<{ kind: RuleKind; param: number }>({ kind: "streak", param: 3 });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const list: Instrument[] = [];
        const idxList: [string, string][] = [
          ["ndx", "纳指综合"], ["spx", "标普500"], ["ndx100", "纳指100"],
        ];
        for (const [key, label] of idxList) {
          const idx = await loadIndex(key);
          list.push({ id: `idx-${key}`, label: `${label}（指数）`, points: idx.points, hasPremium: false });
        }
        let s: Summary | null = null;
        try { s = await loadSummary(); } catch { /* 数据未生成时只提供指数回测 */ }
        if (s) {
          setSummary(s);
          for (const [code, f] of Object.entries(s.funds)) {
            if (!f.market) continue;
            try {
              const [nav, prem] = await Promise.all([loadNav(code), loadPremium(code)]);
              const pmap = new Map(prem.map(([d, , , p]) => [d, p]));
              list.push({
                id: `fund-${code}`, label: `${f.name}（场内）`, points: nav,
                premiumMap: pmap, hasPremium: true,
              });
            } catch { /* 该基金无数据则跳过 */ }
          }
        }
        setInstruments(list);
      } catch (e) {
        setErr(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const inst = instruments.find((i) => i.id === selId);

  const result = useMemo(() => {
    if (!inst) return null;
    const premSeries = inst.hasPremium && inst.premiumMap
      ? inst.points.map(([d]) => inst.premiumMap!.get(d) ?? null)
      : undefined;
    const r = runBacktest(inst.points, rule, HORIZONS, premSeries);
    const bench = runBacktest(inst.points, { kind: "any", param: 0 }, HORIZONS);
    return { r, bench };
  }, [inst, rule]);

  if (err) return <ErrorBlock msg={`数据加载失败：${err}`} />;
  if (loading) return <Loading text="加载回测数据…" />;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="胜率回测"
        sub="规则在历史数据中触发的日子买入，持有 N 个交易日后的收益统计。全部计算在你的浏览器里完成，调参即时生效。灰字 = 样本 <30，统计意义弱，别当真。"
      />

      <Card className="space-y-4 p-4">
        {/* 标的 */}
        <div>
          <div className="mb-1.5 text-xs text-zinc-500">回测标的</div>
          <div className="flex flex-wrap gap-1.5">
            {instruments.map((i) => (
              <button key={i.id}
                className={`rounded-lg px-2.5 py-1 text-xs transition-colors ${
                  selId === i.id ? "bg-sky-500/20 font-medium text-sky-300" : "text-zinc-500 hover:bg-zinc-800"
                }`}
                onClick={() => setSelId(i.id)}>
                {i.label}
              </button>
            ))}
          </div>
          {inst && (
            <div className="mt-1.5 text-[11px] text-zinc-600">
              样本区间 {inst.points[0]?.[0]} ~ {inst.points.at(-1)?.[0]}，共 {inst.points.length} 个交易日
              {summary && ` ｜ 数据更新于 ${summary.generated_at}`}
            </div>
          )}
        </div>

        {/* 规则 */}
        <div>
          <div className="mb-1.5 text-xs text-zinc-500">买入规则</div>
          <div className="flex flex-wrap gap-1.5">
            {RULES.filter((r) => r.kind !== "premiumLe" || inst?.hasPremium).map((r) => (
              <button key={r.kind}
                className={`rounded-lg px-2.5 py-1 text-xs transition-colors ${
                  rule.kind === r.kind ? "bg-zinc-800 font-medium text-zinc-100" : "text-zinc-500 hover:bg-zinc-900"
                }`}
                onClick={() => setRule({ kind: r.kind, param: r.params[1]?.v ?? r.params[0].v })}>
                {r.label}
              </button>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {RULES.find((r) => r.kind === rule.kind)?.params.map((p) => (
              <button key={p.v}
                className={`num rounded-md border px-2 py-0.5 text-xs transition-colors ${
                  rule.param === p.v
                    ? "border-sky-500/50 bg-sky-500/15 text-sky-300"
                    : "border-zinc-800 text-zinc-500 hover:border-zinc-700"
                }`}
                onClick={() => setRule((r) => ({ ...r, param: p.v }))}>
                {p.t}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {result && inst && (
        <Card className="p-4">
          <TableWrap>
            <thead>
              <tr>
                <Th>持有期</Th>
                {HORIZONS.map((h) => <Th key={h}>{h} 个交易日</Th>)}
              </tr>
            </thead>
            <tbody>
              <tr className="hover:bg-zinc-900/60">
                <Td className="font-medium text-zinc-200">规则触发日买入</Td>
                {HORIZONS.map((h) => <Td key={h}><StatCell s={result.r[h]} /></Td>)}
              </tr>
              <tr className="text-zinc-400 hover:bg-zinc-900/60">
                <Td>基准：任意一天买入</Td>
                {HORIZONS.map((h) => <Td key={h}><StatCell s={result.bench[h]} /></Td>)}
              </tr>
            </tbody>
          </TableWrap>
          <p className="mt-3 text-[11px] leading-relaxed text-zinc-600">
            单元格 = 胜率 / 平均收益 / 样本数 / 盈亏比（平均盈利 ÷ 平均亏损）。
            判断一个信号是否有用：胜率和平均收益都要<b className="text-zinc-400">同时</b>显著好于基准行，且样本够大。
            长期牛市里几乎所有买入规则的基准胜率都在 55% 以上——这不代表信号有效。
            历史统计不代表未来，不构成投资建议。
          </p>
        </Card>
      )}

      {/* 规则速查：当前标的全部规则 × 5日胜率 */}
      {inst && (
        <Card className="p-4">
          <SectionTitle title="规则速查（持有 5 日）" sub="一眼扫过所有规则的有效性，标绿 = 明显优于基准" />
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {RULES.filter((r) => r.kind !== "premiumLe" || inst.hasPremium).flatMap((r) =>
              r.params.map((p) => {
                const premSeries = inst.hasPremium && inst.premiumMap
                  ? inst.points.map(([d]) => inst.premiumMap!.get(d) ?? null) : undefined;
                const st = runBacktest(inst.points, { kind: r.kind, param: p.v }, [5], premSeries)[5];
                const b5 = result?.bench[5];
                const better = b5 && st.n >= 30 && st.winRate! > b5.winRate! + 3 && st.avg! > b5.avg!;
                return (
                  <div key={`${r.kind}-${p.v}`}
                    className={`flex items-baseline justify-between rounded-lg border px-3 py-1.5 text-xs ${
                      better ? "border-emerald-500/30 bg-emerald-500/5" : "border-zinc-800/70"
                    }`}>
                    <button className="text-zinc-300 hover:text-sky-300"
                      onClick={() => setRule({ kind: r.kind, param: p.v })}>
                      {r.label.replace("X%", "").replace("N", "")}{p.t}
                    </button>
                    <span className={`num ${st.n < 30 ? "text-zinc-600" : better ? "text-emerald-400" : "text-zinc-400"}`}>
                      {st.n === 0 ? "-" : `${st.winRate!.toFixed(1)}% (n=${st.n})`}
                    </span>
                  </div>
                );
              }),
            )}
          </div>
          <p className="mt-2 text-[11px] text-zinc-600">点任意一条可切换到上方详细计算。基准 5 日胜率：{result ? fmtPct(result.bench[5].winRate, 1) : "-"}</p>
        </Card>
      )}
    </div>
  );
}
