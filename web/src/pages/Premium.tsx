import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Card, ErrorBlock, Loading, PremText, SectionTitle, TableWrap, Td, Th, fmtNum, fmtPct, premColor } from "../components/ui";
import { loadPremium, loadSummary } from "../lib/data";
import { fetchTencentQuotes, toTencentCode } from "../lib/realtime";
import { percentile } from "../lib/stats";
import type { Point4, Summary } from "../lib/types";

function PremChart({ points, name }: { points: Point4[]; name: string }) {
  const data = points.map(([d, , , p]) => ({ d, p }));
  const mean30 = useMemo(() => {
    const out: (number | null)[] = [];
    for (let i = 0; i < data.length; i++) {
      const w = data.slice(Math.max(0, i - 29), i + 1);
      out.push(w.reduce((a, b) => a + b.p, 0) / w.length);
    }
    return out;
  }, [data]);
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data.map((x, i) => ({ ...x, m: mean30[i] }))} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
          <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 11 }} minTickGap={56} />
          <YAxis tick={{ fill: "#71717a", fontSize: 11 }} unit="%" width={52} />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#a1a1aa" }}
          />
          <ReferenceLine y={0} stroke="#52525b" />
          <ReferenceLine y={3} stroke="#f59e0b" strokeDasharray="4 4" />
          <ReferenceLine y={10} stroke="#e11d48" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="p" name={`${name} 溢价%`} stroke="#38bdf8" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="m" name="30日均值" stroke="#a1a1aa" dot={false} strokeWidth={1} strokeDasharray="4 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Premium() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [hists, setHists] = useState<Record<string, Point4[]>>({});
  const [sel, setSel] = useState<string | null>(null);
  const [rt, setRt] = useState<Record<string, number>>({});
  const [err, setErr] = useState("");

  useEffect(() => {
    loadSummary()
      .then((s) => {
        setSummary(s);
        const market = Object.entries(s.funds).filter(([, f]) => f.market);
        return Promise.all(
          market.map(async ([code]) => [code, await loadPremium(code).catch((): Point4[] => [])] as [string, Point4[]]),
        ).then((entries) => {
          setHists(Object.fromEntries(entries));
          if (entries.length) setSel(entries[0][0]);
        });
      })
      .catch((e) => setErr(String(e)));
  }, []);

  // 实时溢价升级
  useEffect(() => {
    if (!summary) return;
    const codes = Object.entries(summary.funds)
      .filter(([, f]) => f.market)
      .map(([code, f]) => toTencentCode(code, f.market)!);
    fetchTencentQuotes(codes)
      .then((qs) => {
        const out: Record<string, number> = {};
        for (const [key, q] of Object.entries(qs)) {
          const nav = summary.funds[key]?.card?.nav;
          if (nav) out[key] = (q.price - nav) / nav * 100;
        }
        setRt(out);
      })
      .catch(() => setRt({}));
  }, [summary]);

  if (err) return <ErrorBlock msg={`数据加载失败：${err}`} />;
  if (!summary) return <Loading text="加载溢价数据…" />;

  const rows = Object.entries(summary.funds)
    .filter(([, f]) => f.market && f.card)
    .map(([code, f]) => {
      const hist = hists[code] ?? [];
      const prems = hist.map((p) => p[3]);
      const cur = rt[code] ?? f.card!.premium_now ?? f.card!.premium_close ?? null;
      return { code, f, cur, n: hist.length,
        p30: percentile(prems, 30), p90: percentile(prems, 90), p365: percentile(prems, 365) };
    });

  const selHist = sel ? hists[sel] ?? [] : [];
  const selName = sel ? summary.funds[sel]?.name : "";

  return (
    <div className="space-y-6">
      <SectionTitle
        title="场内溢价监控"
        sub={`溢价 = 场内价 ÷ 最新披露净值 - 1（QDII 净值为 T-1 美股收盘口径）。实时值来自浏览器直连腾讯行情；分位 = 当前溢价在过去 N 个交易日中的位置，越高说明越偏离常态。`}
      />

      <Card className="p-4">
        <TableWrap>
          <thead>
            <tr>
              <Th>基金</Th><Th>现价</Th><Th>溢价(实时)</Th><Th>溢价(收盘)</Th>
              <Th>30日分位</Th><Th>90日分位</Th><Th>365日分位</Th><Th>历史样本</Th><Th></Th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ code, f, cur, n, p30, p90, p365 }) => (
              <tr key={code} className="cursor-pointer hover:bg-zinc-900/60" onClick={() => setSel(code)}>
                <Td>
                  <span className="text-zinc-200">{f.name}</span>
                  <span className="ml-1.5 text-[11px] text-zinc-500">{code}</span>
                </Td>
                <Td>{rt[code] != null && f.card!.nav ? fmtNum(f.card!.nav * (1 + cur! / 100), 3) : "-"}</Td>
                <Td className={premColor(cur)}>{fmtPct(cur)}</Td>
                <Td><PremText v={f.card!.premium_close} /></Td>
                <Td className="text-zinc-400">{p30 == null ? "-" : `${p30.toFixed(0)}%`}</Td>
                <Td className="text-zinc-400">{p90 == null ? "-" : `${p90.toFixed(0)}%`}</Td>
                <Td className="text-zinc-400">{p365 == null ? "-" : `${p365.toFixed(0)}%`}</Td>
                <Td className="text-zinc-500">{n} 天</Td>
                <Td>{sel === code && <span className="text-[11px] text-sky-400">查看中</span>}</Td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </Card>

      {sel && selHist.length > 0 && (
        <Card className="p-4">
          <SectionTitle title={`${selName} 溢价历史`} sub="黄虚线 = 3% 警戒线，红虚线 = 10% 高危线" />
          <PremChart points={selHist} name={selName} />
        </Card>
      )}
    </div>
  );
}
