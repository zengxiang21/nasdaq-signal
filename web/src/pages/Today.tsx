import { useEffect, useState } from "react";
import { Card, ErrorBlock, Loading, RatingBadge, StatusChip, TableWrap, Td, Th, fmtNum, fmtPct, premColor } from "../components/ui";
import { loadSummary } from "../lib/data";
import { fetchTencentQuotes, toTencentCode } from "../lib/realtime";
import type { FundCard, Summary, SummaryFund } from "../lib/types";

/** 腾讯实时价 → 实时溢价（市价 vs 最新净值） */
function useRealtimePremium(summary: Summary | null) {
  const [rt, setRt] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!summary) return;
    const codes = Object.entries(summary.funds)
      .filter(([, f]) => f.market)
      .map(([code, f]) => toTencentCode(code, f.market)!);
    fetchTencentQuotes(codes)
      .then((qs) => {
        const out: Record<string, number> = {};
        for (const [key, q] of Object.entries(qs)) {
          const f = summary.funds[key];
          const nav = f?.card?.nav;
          if (f?.card && nav) out[key] = (q.price - nav) / nav * 100;
        }
        setRt(out);
      })
      .catch(() => setRt({}));
  }, [summary]);
  return rt;
}

/** 温度计横条 */
function TempGauge({ temp, level }: { temp: number | null; level: string }) {
  const pos = temp == null ? 50 : Math.max(0, Math.min(100, temp));
  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-3xl font-bold num">
            {temp == null ? "-" : temp.toFixed(0)}
            <span className="ml-1 text-base font-normal text-zinc-500">°贪婪</span>
          </div>
          <div className={`mt-0.5 text-sm font-medium ${
            pos >= 70 ? "text-rose-400" : pos >= 45 ? "text-amber-400" : pos >= 25 ? "text-zinc-300" : "text-sky-400"
          }`}>
            {temp == null ? "数据不足" : level}
          </div>
        </div>
        <div className="text-right text-[11px] leading-relaxed text-zinc-500">
          100=溢价最贵+限购最挤<br />0=便宜+宽松
        </div>
      </div>
      <div className="relative mt-3 h-2.5 rounded-full bg-gradient-to-r from-sky-500 via-amber-500 to-rose-600">
        <div
          className="absolute top-1/2 h-4 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-zinc-950 bg-zinc-100"
          style={{ left: `${pos}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-zinc-600">
        <span>冰点</span><span>中性</span><span>偏热</span><span>过热</span>
      </div>
    </div>
  );
}

/** 单指数决策卡 */
function DecisionCard({ indexName, funds, rt }: { indexName: string; funds: [string, SummaryFund][]; rt: Record<string, number> }) {
  const market = funds.filter(([, f]) => f.market && f.card);
  const otc = funds.filter(([, f]) => !f.market && f.card);

  const prem = (code: string, f: SummaryFund): number | null => {
    if (rt[code] != null) return rt[code];
    return f.card?.premium_now ?? f.card?.premium_close ?? null;
  };

  const bestMarket = market
    .map(([code, f]) => ({ code, f, p: prem(code, f) }))
    .filter((x) => x.p != null)
    .sort((a, b) => a.p! - b.p!)[0];

  const bestOtc = otc
    .map(([code, f]) => ({
      code, f,
      limit: f.limits?.daily_limit ?? -1,
      status: f.limits?.status_buy,
      // 暂停申购的不能算"可走"，排到最后
      buyable: !(f.limits?.status_buy ?? "").includes("暂停") &&
               !(f.limits?.status_buy ?? "").includes("关闭"),
    }))
    .sort((a, b) => (Number(b.buyable) - Number(a.buyable)) || (b.limit - a.limit))[0];

  let advice = <span className="text-zinc-500">暂无数据</span>;
  const otcBuyable = bestOtc?.buyable
    ? `场外可走 ${bestOtc.f.name}${bestOtc.f.share ? `(${bestOtc.f.share})` : ""}${bestOtc.limit >= 0 ? ` · 限额 ${bestOtc.limit >= 10000 ? `${bestOtc.limit / 10000}万` : bestOtc.limit} 元/日` : ""}`
    : "场外全部暂停/限购";
  if (bestMarket?.p != null) {
    const p = bestMarket.p;
    if (p >= 10) {
      advice = <span className="text-rose-400">场内溢价 {p.toFixed(1)}%，买入即亏溢价，<b>勿追</b>。{otcBuyable}</span>;
    } else if (p >= 3) {
      advice = <span className="text-orange-400">场内溢价 {p.toFixed(1)}% 偏贵，等回落或{otcBuyable}。</span>;
    } else if (p >= 1) {
      advice = <span className="text-amber-400">场内溢价 {p.toFixed(1)}%，可少量买入。</span>;
    } else {
      advice = <span className="text-emerald-400">场内溢价 {fmtPct(p)}（折价/低位），可买入。</span>;
    }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-zinc-100">{indexName}</h3>
        {bestMarket?.f.card && <RatingBadge rating={bestMarket.f.card.rating} />}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <div className="text-[11px] text-zinc-500">最优场内溢价</div>
          <div className={`text-xl font-bold ${premColor(bestMarket?.p ?? null)}`}>
            {fmtPct(bestMarket?.p ?? null)}
          </div>
          <div className="text-[11px] text-zinc-500">{bestMarket ? `${bestMarket.f.name} ${bestMarket.code}` : "-"}</div>
        </div>
        <div>
          <div className="text-[11px] text-zinc-500">最优场外限额</div>
          <div className="text-xl font-bold num text-zinc-100">
            {bestOtc
              ? bestOtc.buyable && bestOtc.limit >= 0
                ? `${bestOtc.limit >= 10000 ? `${bestOtc.limit / 10000}万` : bestOtc.limit}元`
                : "暂停"
              : "-"}
          </div>
          <div className="text-[11px] text-zinc-500">{bestOtc ? bestOtc.f.name : "-"}</div>
        </div>
        <div>
          <div className="text-[11px] text-zinc-500">最优场外评分</div>
          <div className="text-xl font-bold num text-zinc-100">{fmtNum(bestOtc?.f.card?.score, 1)}</div>
          <div className="text-[11px] text-zinc-500">{bestOtc?.f.card && <RatingBadge rating={bestOtc.f.card.rating} className="scale-90 origin-left" />}</div>
        </div>
        <div>
          <div className="text-[11px] text-zinc-500">最新净值日</div>
          <div className="text-xl font-bold num text-zinc-100">{bestMarket?.f.card?.nav_date.slice(5) ?? "-"}</div>
          <div className="text-[11px] text-zinc-500">QDII 为 T-1 美股收盘口径</div>
        </div>
      </div>
      <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2.5 text-sm">
        💡 {advice}
      </div>
    </Card>
  );
}

export default function Today() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [err, setErr] = useState("");
  const rt = useRealtimePremium(summary);

  useEffect(() => {
    loadSummary().then(setSummary).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorBlock msg={`数据加载失败：${err}`} />;
  if (!summary) return <Loading text="加载今日信号…" />;

  const t = summary.temperature;
  const byIndex = (name: string): [string, SummaryFund][] =>
    Object.entries(summary.funds).filter(([, f]) => f.index_name === name);
  const nasdaq = byIndex("纳斯达克100");
  const sp = byIndex("标普500");

  const rows = Object.entries(summary.funds).sort((a, b) => {
    const ka = a[1].market ? 0 : 1;   // 场内在前
    const kb = b[1].market ? 0 : 1;
    return ka - kb || (b[1].card?.score ?? 0) - (a[1].card?.score ?? 0);
  });

  return (
    <div className="space-y-6">
      {/* 温度计 */}
      <Card className="p-5">
        <div className="flex flex-col gap-6 md:flex-row md:items-center">
          <div className="flex-1">
            <TempGauge temp={t.temp} level={t.level} />
          </div>
          <div className="grid grid-cols-3 gap-4 text-center md:w-80">
            <div>
              <div className="num text-lg font-semibold text-zinc-100">{fmtPct(t.premium_median)}</div>
              <div className="text-[11px] text-zinc-500">场内溢价中位数</div>
            </div>
            <div>
              <div className="num text-lg font-semibold text-zinc-100">{fmtPct(t.crowd_ratio, 0, false)}</div>
              <div className="text-[11px] text-zinc-500">场外限购拥挤度</div>
            </div>
            <div>
              <div className="num text-lg font-semibold text-zinc-100">{t.n_market}/{t.n_otc}</div>
              <div className="text-[11px] text-zinc-500">场内/场外覆盖数</div>
            </div>
          </div>
        </div>
      </Card>

      {/* 决策卡 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DecisionCard indexName="纳斯达克100" funds={nasdaq} rt={rt} />
        <DecisionCard indexName="标普500" funds={sp} rt={rt} />
      </div>

      {/* 全部基金 */}
      <Card className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-zinc-300">全部基金（{rows.length} 只）</h2>
          <span className="text-[11px] text-zinc-600">更新于 {summary.generated_at}</span>
        </div>
        <TableWrap>
          <thead>
            <tr>
              <Th>基金</Th><Th>评分</Th><Th>评级</Th><Th>场内溢价</Th>
              <Th>净值</Th><Th>RSI</Th><Th>60日回撤</Th><Th>申购状态</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([code, f]) => {
              const c: FundCard | null = f.card;
              const p = rt[code] ?? c?.premium_now ?? c?.premium_close ?? null;
              return (
                <tr key={code} className="hover:bg-zinc-900/60">
                  <Td>
                    <span className="text-zinc-200">{f.name}</span>
                    <span className="ml-1.5 text-[11px] text-zinc-500">{code}{f.share ? ` · ${f.share}` : ""}{f.market ? "" : " · 场外"}</span>
                  </Td>
                  <Td className="font-semibold">{fmtNum(c?.score, 1)}</Td>
                  <Td>{c ? <RatingBadge rating={c.rating} /> : "-"}</Td>
                  <Td className={premColor(p)}>{f.market ? fmtPct(p) : "场外"}</Td>
                  <Td>{fmtNum(c?.nav, 4)}</Td>
                  <Td>{fmtNum(c?.rsi, 1)}</Td>
                  <Td className="text-zinc-400">{fmtPct(c?.dd60, 1)}</Td>
                  <Td>
                    {f.market
                      ? <span className="text-[11px] text-zinc-600">—</span>
                      : f.limits ? <StatusChip status={f.limits.status_buy} limit={f.limits.daily_limit} /> : "-"}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </TableWrap>
        <p className="mt-3 text-[11px] leading-relaxed text-zinc-600">
          评分 = 溢价30% + RSI25% + 60日回撤20% + 均线偏离15% + 估值分位10%（详见「说明」）；场内溢价 ≥10% 一票否决标 🚫，
          溢价优先看实时值（浏览器直连腾讯行情），回落到静态值时为收盘口径。
        </p>
      </Card>
    </div>
  );
}
