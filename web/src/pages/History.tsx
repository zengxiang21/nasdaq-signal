import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Card, ErrorBlock, Loading, SectionTitle, TableWrap, Td, Th, fmtNum, fmtPct } from "../components/ui";
import { INDEX_KEYS, loadIndex } from "../lib/data";
import { normalizePair, streakForwardStats, yearlyStats } from "../lib/stats";
import type { IndexData } from "../lib/types";

function ReturnBars({ data }: { data: { year: number; ret: number | null }[] }) {
  const rows = data.filter((d) => d.ret != null).map((d) => ({ year: String(d.year), ret: d.ret! }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "#71717a", fontSize: 10 }} interval={Math.max(0, Math.floor(rows.length / 20) - 1)} />
          <YAxis tick={{ fill: "#71717a", fontSize: 11 }} unit="%" width={56} />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#a1a1aa" }}
            formatter={(v: number) => [`${v.toFixed(1)}%`, "年度收益"]}
          />
          <Bar dataKey="ret" name="年度收益%">
            {rows.map((r, i) => (
              <Cell key={i} fill={r.ret >= 0 ? "#34d399" : "#f87171"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function History() {
  const [key, setKey] = useState<string>("ndx");
  const [data, setData] = useState<Record<string, IndexData>>({});
  const [other, setOther] = useState<IndexData | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    loadIndex(key).then((d) => setData((m) => ({ ...m, [key]: d }))).catch((e) => setErr(String(e)));
  }, [key]);

  const idx = data[key];
  const years = useMemo(() => (idx ? yearlyStats(idx.points) : []), [idx]);

  // 复利对比：当前指数 vs 另一条长历史（ndx↔spx）
  useEffect(() => {
    const otherKey = key === "spx" ? "ndx" : "spx";
    if (key === "ndx100") { setOther(null); return; }
    loadIndex(otherKey).then(setOther).catch(() => setOther(null));
  }, [key]);

  const compare = useMemo(() => {
    if (!idx || !other) return null;
    return normalizePair(idx.points, other.points);
  }, [idx, other]);

  const streakStats = useMemo(() => {
    if (!idx) return [];
    const closes = idx.points.map((p) => p[1]);
    return [2, 3, 4, 5, 6].map((k) => ({ k, ...streakForwardStats(closes, k, 5) }));
  }, [idx]);

  if (err) return <ErrorBlock msg={`数据加载失败：${err}`} />;

  const posYears = years.filter((y) => (y.ret ?? 0) > 0).length;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="长历史统计"
        sub="对长期定投者：把「每年赚多少、最多亏多少」放到 40 年维度看，比任何短线信号都更能稳定心态"
      />

      <div className="flex flex-wrap gap-2">
        {INDEX_KEYS.map((k) => (
          <button key={k.key}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              key === k.key ? "bg-zinc-800 font-medium text-zinc-100" : "text-zinc-500 hover:bg-zinc-900"
            }`}
            onClick={() => setKey(k.key)}>
            {k.label}
          </button>
        ))}
      </div>

      {!idx ? <Loading text="加载指数历史…" /> : (
        <>
          {idx.note && (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5 text-xs text-zinc-400">
              ℹ️ {idx.note}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-4">
            <Card className="p-4">
              <div className="text-[11px] text-zinc-500">统计区间</div>
              <div className="num text-xl font-bold text-zinc-100">{idx.points[0]?.[0].slice(0, 4)}–{idx.points.at(-1)?.[0].slice(0, 4)}</div>
              <div className="text-[11px] text-zinc-500">{idx.points.length} 个交易日</div>
            </Card>
            <Card className="p-4">
              <div className="text-[11px] text-zinc-500">上涨年份占比</div>
              <div className="num text-xl font-bold text-emerald-400">{years.length ? (posYears / years.length * 100).toFixed(0) : "-"}%</div>
              <div className="text-[11px] text-zinc-500">{posYears}/{years.length} 年</div>
            </Card>
            <Card className="p-4">
              <div className="text-[11px] text-zinc-500">最惨年份</div>
              <div className="num text-xl font-bold text-red-400">
                {fmtPct(years.reduce((m, y) => Math.min(m, y.ret ?? 0), 0), 1)}
              </div>
              <div className="text-[11px] text-zinc-500">
                {years.reduce((m, y) => (y.ret ?? 0) < (m?.ret ?? 0) ? y : m, years[0])?.year ?? "-"} 年
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-[11px] text-zinc-500">最差年回撤</div>
              <div className="num text-xl font-bold text-rose-400">
                {fmtPct(years.reduce((m, y) => Math.min(m, y.maxDrawdown ?? 0), 0), 1)}
              </div>
              <div className="text-[11px] text-zinc-500">年内峰谷最大跌幅</div>
            </Card>
          </div>

          <Card className="p-4">
            <SectionTitle title="逐年收益" sub="绿色=上涨，红色=下跌；时间会抹平大部分波动，前提是你在场" />
            <ReturnBars data={years} />
            <div className="mt-4 max-h-96 overflow-y-auto">
              <TableWrap>
                <thead>
                  <tr><Th>年份</Th><Th>年度收益</Th><Th>年内最大回撤</Th><Th>年末收盘</Th></tr>
                </thead>
                <tbody>
                  {[...years].reverse().map((y) => (
                    <tr key={y.year} className="hover:bg-zinc-900/60">
                      <Td>{y.year}</Td>
                      <Td className={(y.ret ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}>{fmtPct(y.ret, 1)}</Td>
                      <Td className="text-zinc-400">{fmtPct(y.maxDrawdown, 1)}</Td>
                      <Td className="text-zinc-500">{fmtNum(y.end, 2)}</Td>
                    </tr>
                  ))}
                </tbody>
              </TableWrap>
            </div>
          </Card>

          {compare && compare.dates.length > 0 && (
            <Card className="p-4">
              <SectionTitle title="纳指 vs 标普500 复利对比" sub={`从共同起点归一化为 1（${compare.dates[0]} 至今）——纳指长期跑赢，但波动与回撤也更大`} />
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={compare.dates.map((d, i) => ({ d, a: compare.a[i], b: compare.b[i] }))}
                    margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
                    <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
                    <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 11 }} minTickGap={56} />
                    <YAxis tick={{ fill: "#71717a", fontSize: 11 }} width={52} />
                    <Tooltip
                      contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "#a1a1aa" }}
                      formatter={(v: number) => [`${v.toFixed(2)}x`]}
                    />
                    <Line type="monotone" dataKey="a" name={idx.name} stroke="#38bdf8" dot={false} strokeWidth={1.5} />
                    <Line type="monotone" dataKey="b" name={other?.name ?? ""} stroke="#a78bfa" dot={false} strokeWidth={1.5} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 text-center text-xs">
                <span className="text-sky-400">{idx.name} {compare.a.at(-1)?.toFixed(2)}x</span>
                <span className="mx-3 text-zinc-600">vs</span>
                <span className="text-violet-400">{other?.name} {compare.b.at(-1)?.toFixed(2)}x</span>
              </div>
            </Card>
          )}

          <Card className="p-4">
            <SectionTitle title="连跌统计" sub="连跌 k 天结束后，之后 5 个交易日的表现——看看「越跌越买」在历史上是什么体验" />
            <TableWrap>
              <thead>
                <tr><Th>连跌天数</Th><Th>发生次数</Th><Th>后5日胜率</Th><Th>后5日平均涨跌</Th></tr>
              </thead>
              <tbody>
                {streakStats.map((s) => (
                  <tr key={s.k} className="hover:bg-zinc-900/60">
                    <Td>≥ {s.k} 天</Td>
                    <Td>{s.count}</Td>
                    <Td className="text-zinc-300">{s.winRate.toFixed(1)}%</Td>
                    <Td className={s.avg >= 0 ? "text-emerald-400" : "text-red-400"}>{fmtPct(s.avg, 2)}</Td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
            <p className="mt-3 text-[11px] text-zinc-600">
              样本为 {idx.points[0]?.[0]} 至今全部交易日；短连跌后的反弹只是统计常态，2008 年那种连跌照样接飞刀——仓位比信号重要。
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
