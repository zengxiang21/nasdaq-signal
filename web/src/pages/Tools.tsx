import { useEffect, useMemo, useState } from "react";
import { Card, Loading, SectionTitle, TableWrap, Td, Th, fmtPct } from "../components/ui";
import { INDEX_KEYS, loadIndex } from "../lib/data";
import { fetchTencentQuotes } from "../lib/realtime";
import type { IndexData } from "../lib/types";

// ---------------- A/C 类费率计算器 ----------------
function ACFeeCalc() {
  const [amount, setAmount] = useState(10000);
  const [days, setDays] = useState(365);
  const [gain, setGain] = useState(10);       // 预期净值涨幅 %
  const [rate, setRate] = useState(1.5);      // A类申购费率（原价）%
  const [disc, setDisc] = useState(0.1);      // 申购费折扣（0.1 = 一折）
  const [svc, setSvc] = useState(0.8);        // C类销售服务费率（年化）%

  const calc = useMemo(() => {
    // A类：外扣法申购费 + 赎回费（<7天 1.5%，QDII 常见档）
    const effRate = rate * disc;
    const netInvest = amount / (1 + effRate);
    const subFee = amount - netInvest;
    const grossA = netInvest * (1 + gain / 100);
    const redeemA = days < 7 ? grossA * 0.015 : 0;
    const finalA = grossA - redeemA;

    // C类：无申购费，销售服务费按年化×持有天数近似计提，<7天赎回费 1.5%
    const grossC = amount * (1 + gain / 100);
    const svcFee = amount * (svc / 100) * days / 365;
    const redeemC = days < 7 ? grossC * 0.015 : 0;
    const finalC = grossC - svcFee - redeemC;

    // 盈亏平衡持有天数：profitA = profitC（数值扫描）
    let breakEven: number | null = null;
    for (let d = 8; d <= 1825; d++) {
      const pa = (amount / (1 + effRate)) * (1 + gain / 100) - amount;
      const pc = amount * (1 + gain / 100) - amount * (svc / 100) * d / 365 - amount;
      if (pc >= pa) { breakEven = d; break; }
    }
    return { subFee, redeemA, finalA, svcFee, redeemC, finalC, breakEven };
  }, [amount, days, gain, rate, disc, svc]);

  const profitA = calc.finalA - amount;
  const profitC = calc.finalC - amount;
  const feeA = calc.subFee + calc.redeemA;
  const feeC = calc.svcFee + calc.redeemC;
  const cWins = profitC >= profitA;

  const numInput = (label: string, value: number, set: (v: number) => void, step: number, suffix: string, hint?: string) => (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}{hint && <span className="ml-1 text-zinc-600">{hint}</span>}</span>
      <span className="flex items-center rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 focus-within:border-sky-500/50">
        <input type="number" step={step} value={value}
          onChange={(e) => set(Number(e.target.value) || 0)}
          className="num w-full bg-transparent py-1.5 text-sm text-zinc-200 outline-none" />
        <span className="text-xs text-zinc-600">{suffix}</span>
      </span>
    </label>
  );

  return (
    <Card className="p-4">
      <SectionTitle title="A/C 类持有成本计算器" sub="QDII 指数基金 A 类收申购费、C 类免申购费但按日计提销售服务费——持有多久选哪类，一算便知" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {numInput("申购金额", amount, setAmount, 1000, "元")}
        {numInput("预期持有", days, setDays, 30, "天")}
        {numInput("预期涨幅", gain, setGain, 1, "%")}
        {numInput("A申购费率", rate, setRate, 0.1, "%")}
        {numInput("费率折扣", disc, setDisc, 0.05, "折", "(0.1=一折)")}
        {numInput("C销售服务费", svc, setSvc, 0.05, "%/年")}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className={`rounded-lg border p-4 ${cWins ? "border-zinc-800" : "border-emerald-500/40 bg-emerald-500/5"}`}>
          <div className="flex justify-between text-sm text-zinc-400">
            <span>A 类（申购费 {rate}%×{disc === 0.1 ? "一折" : disc + "折"} = {(rate * disc).toFixed(2)}%）</span>
          </div>
          <div className="num mt-1 text-2xl font-bold text-zinc-100">{fmtPct(profitA / amount * 100, 2)}</div>
          <div className="mt-1 text-xs text-zinc-500">
            净赚 {profitA.toFixed(0)} 元 ｜ 总费用 {feeA.toFixed(0)} 元（申购 {calc.subFee.toFixed(0)} + 赎回 {calc.redeemA.toFixed(0)}）
          </div>
        </div>
        <div className={`rounded-lg border p-4 ${cWins ? "border-emerald-500/40 bg-emerald-500/5" : "border-zinc-800"}`}>
          <div className="flex justify-between text-sm text-zinc-400">
            <span>C 类（销售服务费 {svc}%/年）</span>
          </div>
          <div className="num mt-1 text-2xl font-bold text-zinc-100">{fmtPct(profitC / amount * 100, 2)}</div>
          <div className="mt-1 text-xs text-zinc-500">
            净赚 {profitC.toFixed(0)} 元 ｜ 总费用 {feeC.toFixed(0)} 元（服务费 {calc.svcFee.toFixed(0)} + 赎回 {calc.redeemC.toFixed(0)}）
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2.5 text-sm">
        💡 持有 {days} 天：<b className={cWins ? "text-emerald-400" : "text-sky-400"}>{cWins ? "C 类更划算" : "A 类更划算"}</b>
        {calc.breakEven != null && <>（分界点约 <b className="num">{calc.breakEven}</b> 天：短于它选 C，长于它选 A）</>}
        。A/C 类赎回费均按「持有 &lt;7 天收 1.5%」计算（监管强制短炒惩罚费）。
      </div>
      <p className="mt-2 text-[11px] text-zinc-600">
        计算为近似口径：C 类服务费按初始金额×年化费率×天数/365 线性计提，实际按每日净值计提；不同基金费率档不同，
        以基金合同为准，请按实际费率修改上方参数。
      </p>
    </Card>
  );
}

// ---------------- 小算盘：回本测算 + 汇率换算 ----------------
function RecoveryAndFx() {
  const [loss, setLoss] = useState(20);   // 当前亏损 %
  const [usd, setUsd] = useState(1000);   // 美元金额
  const [rate, setRate] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetchTencentQuotes(["whUSDCNY"])
        .then((qs) => { if (alive && qs.whUSDCNY) setRate(qs.whUSDCNY.price); })
        .catch(() => undefined);
    load();
    const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // 亏损 x% 后回本需涨：x/(1-x)
  const need = (x: number) => x / (100 - x) * 100;
  const rows = [5, 10, 15, 20, 30, 40, 50];

  return (
    <Card className="p-4">
      <SectionTitle title="小算盘" sub="两个最常被问到的数字：亏了要涨多少才回本、美元换人民币多少" />
      <div className="grid gap-4 md:grid-cols-2">
        {/* 回本测算 */}
        <div className="rounded-lg border border-zinc-800/70 p-4">
          <div className="text-sm font-medium text-zinc-200">回本测算</div>
          <label className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
            当前亏损
            <span className="flex items-center rounded-lg border border-zinc-800 bg-zinc-950 px-2 focus-within:border-sky-500/50">
              <input type="number" value={loss} min={1} max={90}
                onChange={(e) => setLoss(Math.min(99, Math.max(1, Number(e.target.value) || 1)))}
                className="num w-16 bg-transparent py-1 text-sm text-zinc-200 outline-none" />
              <span className="text-zinc-600">%</span>
            </span>
            <span className="ml-auto text-zinc-400">
              回本需涨 <b className="num text-lg text-amber-400">{fmtPct(need(loss), 1)}</b>
            </span>
          </label>
          <div className="mt-3 grid grid-cols-4 gap-1.5 sm:grid-cols-7">
            {rows.map((x) => (
              <button key={x}
                className={`num rounded-md border px-1 py-1 text-[11px] ${loss === x ? "border-amber-500/50 bg-amber-500/15 text-amber-300" : "border-zinc-800 text-zinc-500 hover:border-zinc-700"}`}
                onClick={() => setLoss(x)}>
                -{x}%<br />→{need(x).toFixed(1)}%
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-zinc-600">
            亏损越深，回本所需涨幅呈非线性放大——-50% 要 +100% 才回本。这就是为什么控制回撤比抓收益更重要。
          </p>
        </div>

        {/* 汇率换算 */}
        <div className="rounded-lg border border-zinc-800/70 p-4">
          <div className="flex items-baseline justify-between">
            <div className="text-sm font-medium text-zinc-200">美元 ⇄ 人民币</div>
            <div className="num text-xs text-zinc-500">
              USDCNY <b className="text-zinc-200">{rate == null ? "…" : rate.toFixed(4)}</b>
              <span className="ml-1 text-zinc-600">实时</span>
            </div>
          </div>
          <label className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
            美元
            <span className="flex items-center rounded-lg border border-zinc-800 bg-zinc-950 px-2 focus-within:border-sky-500/50">
              <input type="number" value={usd} step={100}
                onChange={(e) => setUsd(Number(e.target.value) || 0)}
                className="num w-24 bg-transparent py-1 text-sm text-zinc-200 outline-none" />
              <span className="text-zinc-600">$</span>
            </span>
          </label>
          <div className="mt-2 num text-2xl font-bold text-zinc-100">
            ¥ {(rate == null ? 0 : usd * rate).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-zinc-600">
            汇率影响 QDII 净值：人民币贬值时期 QDII 有隐性汇率收益，反之亦然。
            场内溢价不含汇率预期修正，仅供换汇参考，实际以银行/渠道牌价为准。
          </p>
        </div>
      </div>
    </Card>
  );
}

// ---------------- 定投日回测 ----------------
function DcaDateTest() {
  const [data, setData] = useState<Record<string, IndexData>>({});
  const [key, setKey] = useState("spx");
  const [freq, setFreq] = useState<"week" | "month">("month");
  const [yearsBack, setYearsBack] = useState(10);

  useEffect(() => {
    if (!data[key]) loadIndex(key).then((d) => setData((m) => ({ ...m, [key]: d }))).catch(() => undefined);
  }, [key, data]);

  const result = useMemo(() => {
    const idx = data[key];
    if (!idx) return null;
    const all = idx.points;
    const startD = new Date();
    startD.setFullYear(startD.getFullYear() - yearsBack);
    const startStr = startD.toISOString().slice(0, 10);
    const pts = all.filter(([d]) => d >= startStr);
    if (pts.length < 100) return null;
    const lastClose = pts.at(-1)![1];

    const simulate = (match: (d: string) => boolean) => {
      let shares = 0, invested = 0, times = 0;
      for (const [d, c] of pts) {
        if (match(d)) { shares += 1000 / c; invested += 1000; times++; }
      }
      if (invested === 0) return null;
      const final = shares * lastClose;
      const daysHeld = Math.max(1, (new Date(pts.at(-1)![0]).getTime() - new Date(pts[0][0]).getTime()) / 86400000);
      const annual = (Math.pow(final / invested, 365 / daysHeld) - 1) * 100;
      // 注意：ret/annual 均为百分数单位（与 fmtPct 一致）
      return { ret: (final / invested - 1) * 100, annual, times, invested, final };
    };

    if (freq === "week") {
      return [0, 1, 2, 3, 4].map((w) => ({
        label: "每周" + "一二三四五"[w],
        ...simulate((d) => new Date(d + "T00:00:00").getDay() === w)!,
      })).filter((x): x is NonNullable<typeof x> => x != null);
    }
    // 每月定投：按月找首个 ≥ d 号的交易日（正确处理顺延）
    return monthlySim(pts);
  }, [key, freq, yearsBack, data]);

  // 每月定投：按月找首个 ≥ d 号的交易日（正确处理顺延）
  function monthlySim(pts: [string, number][]) {
    const byMonth = new Map<string, [string, number][]>();
    for (const p of pts) {
      const mk = p[0].slice(0, 7);
      if (!byMonth.has(mk)) byMonth.set(mk, []);
      byMonth.get(mk)!.push(p);
    }
    return Array.from({ length: 28 }, (_, i) => i + 1).map((day) => {
      let shares = 0, invested = 0, times = 0;
      for (const rows of byMonth.values()) {
        const pick = rows.find(([d]) => Number(d.slice(8, 10)) >= day);
        if (pick) { shares += 1000 / pick[1]; invested += 1000; times++; }
      }
      if (invested === 0) return null;
      const final = shares * pts.at(-1)![1];
      const daysHeld = Math.max(1, (new Date(pts.at(-1)![0]).getTime() - new Date(pts[0][0]).getTime()) / 86400000);
      const annual = (Math.pow(final / invested, 365 / daysHeld) - 1) * 100;
      // ret/annual 为百分数单位（与 fmtPct 一致）
      return { label: `每月${day}日`, ret: (final / invested - 1) * 100, annual, times, invested, final };
    }).filter((x): x is NonNullable<typeof x> => x != null);
  }

  const idx = data[key];
  const isNotNull = <T,>(x: T | null): x is T => x != null;
  const rows = ((result ?? []) as ({ label: string; ret: number; annual: number; times: number } | null)[])
    .filter(isNotNull)
    .sort((a, b) => b.ret - a.ret);
  const best = rows[0], worst = rows.at(-1);

  return (
    <Card className="p-4">
      <SectionTitle title="定投日选择回测" sub="每月几号 / 每周几定投收益最高？——结论先行：差异极小（通常 <0.5%/年），选个方便扣款的日期就好，这里用数据证明给你看" />

      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <div className="flex gap-1">
          {INDEX_KEYS.map((k) => (
            <button key={k.key} onClick={() => setKey(k.key)}
              className={`rounded-lg px-2.5 py-1 text-xs ${key === k.key ? "bg-zinc-800 font-medium text-zinc-100" : "text-zinc-500 hover:bg-zinc-900"}`}>
              {k.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {(["month", "week"] as const).map((f) => (
            <button key={f} onClick={() => setFreq(f)}
              className={`rounded-lg px-2.5 py-1 text-xs ${freq === f ? "bg-zinc-800 font-medium text-zinc-100" : "text-zinc-500 hover:bg-zinc-900"}`}>
              {f === "month" ? "按月" : "按周"}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {[5, 10, 20].map((y) => (
            <button key={y} onClick={() => setYearsBack(y)}
              className={`num rounded-lg px-2.5 py-1 text-xs ${yearsBack === y ? "bg-zinc-800 font-medium text-zinc-100" : "text-zinc-500 hover:bg-zinc-900"}`}>
              近{y}年
            </button>
          ))}
        </div>
        {idx && <span className="num text-[11px] text-zinc-600">{idx.points[0]?.[0]} ~ {idx.points.at(-1)?.[0]}</span>}
      </div>

      {!rows.length ? <Loading text="模拟定投中…" /> : (
        <>
          <div className="mb-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
              <div className="text-[11px] text-zinc-500">最优：{best?.label}</div>
              <div className="num text-lg font-bold text-emerald-400">{fmtPct(best?.ret ?? 0, 2)}</div>
              <div className="text-[11px] text-zinc-500">年化 {fmtPct(best?.annual ?? 0, 2)}</div>
            </div>
            <div className="rounded-lg border border-zinc-800 p-3">
              <div className="text-[11px] text-zinc-500">最差：{worst?.label}</div>
              <div className="num text-lg font-bold text-zinc-300">{fmtPct(worst?.ret ?? 0, 2)}</div>
              <div className="text-[11px] text-zinc-500">年化 {fmtPct(worst?.annual ?? 0, 2)}</div>
            </div>
            <div className="rounded-lg border border-zinc-800 p-3">
              <div className="text-[11px] text-zinc-500">最好 − 最差</div>
              <div className="num text-lg font-bold text-amber-400">{fmtPct((best?.ret ?? 0) - (worst?.ret ?? 0), 2)}</div>
              <div className="text-[11px] text-zinc-500">{"整个持有期的总差距——就这么点"}</div>
            </div>
          </div>
          <TableWrap>
            <thead>
              <tr><Th>定投日</Th><Th>期数</Th><Th>累计收益率</Th><Th>年化</Th><Th></Th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="hover:bg-zinc-900/60">
                  <Td>{r.label}</Td>
                  <Td className="text-zinc-500">{r.times}</Td>
                  <Td className="text-zinc-200">{fmtPct(r.ret, 2)}</Td>
                  <Td className="text-zinc-400">{fmtPct(r.annual, 2)}</Td>
                  <Td>
                    <div className="h-1.5 w-24 rounded bg-zinc-800">
                      <div className="h-1.5 rounded bg-sky-500"
                        style={{ width: `${Math.max(2, 100 * (r.ret - (worst?.ret ?? 0)) / Math.max(0.0001, (best?.ret ?? 1) - (worst?.ret ?? 0)))}%` }} />
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
          <p className="mt-2 text-[11px] text-zinc-600">
            模拟口径：每期 {1000} 元按当日收盘买入（不考虑手续费），遇非交易日顺延到下一交易日。
            任何时候「开始定投并坚持」都比「挑定投日」重要得多。
          </p>
        </>
      )}
    </Card>
  );
}

export default function Tools() {
  return (
    <div className="space-y-6">
      <ACFeeCalc />
      <RecoveryAndFx />
      <DcaDateTest />
    </div>
  );
}
