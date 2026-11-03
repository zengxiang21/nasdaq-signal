import { useEffect, useState } from "react";
import { Card, ErrorBlock, Loading, SectionTitle, StatusChip, TableWrap, Td, Th, fmtNum } from "../components/ui";
import { loadLimits } from "../lib/data";
import type { Limits } from "../lib/types";

const fmtLimit = (v: number | null) =>
  v == null ? "—" : v >= 10000 ? `${v / 10000}万` : v >= 1000 ? v.toLocaleString("zh-CN") : `${v}`;

export default function Limits() {
  const [data, setData] = useState<Limits | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    loadLimits().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorBlock msg={`数据加载失败：${err}`} />;
  if (!data) return <Loading text="加载限额数据…" />;

  const funds = [...data.funds].sort((a, b) => (b.daily_limit ?? -1) - (a.daily_limit ?? -1));
  const buyable = funds.filter((f) =>
    (f.daily_limit ?? 0) > 0 && !(f.status_buy ?? "").includes("暂停") && !(f.status_buy ?? "").includes("关闭"),
  ).length;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="场外限额监控"
        sub={`QDII 额度紧张背景下「哪里还买得进」——数据为天天基金代销渠道口径，实际以办理时渠道规则为准。更新于 ${data.updated_at}`}
      />

      <Card className="p-4">
        <div className="mb-3 flex items-center gap-4 text-xs text-zinc-500">
          <span>覆盖 {funds.length} 只场外基金</span>
          <span className="text-emerald-400">当前 {buyable} 只仍有额度</span>
          <span className="text-zinc-600">按日限额从高到低排序</span>
        </div>
        <TableWrap>
          <thead>
            <tr>
              <Th>基金</Th><Th>指数</Th><Th>申购状态</Th><Th>日累计限额</Th>
              <Th>起购</Th><Th>申购费率</Th><Th>蛋卷可买</Th>
            </tr>
          </thead>
          <tbody>
            {funds.map((f) => (
              <tr key={f.code} className="hover:bg-zinc-900/60">
                <Td>
                  <span className="text-zinc-200">{f.name}</span>
                  <span className="ml-1.5 text-[11px] text-zinc-500">{f.code}{f.share ? ` · ${f.share}` : ""}</span>
                </Td>
                <Td className="text-zinc-400">{f.index_name}</Td>
                <Td><StatusChip status={f.status_buy} limit={null} /></Td>
                <Td className={f.daily_limit == null ? "text-zinc-500" : f.daily_limit <= 100 ? "text-rose-400" : f.daily_limit <= 1000 ? "text-amber-400" : "text-emerald-400"}>
                  {fmtLimit(f.daily_limit)}元
                </Td>
                <Td className="text-zinc-400">{f.min_buy == null ? "—" : `${fmtNum(f.min_buy, 2)}元`}</Td>
                <Td className="text-zinc-400">
                  {f.subscribe_rate == null ? "—"
                    : `${f.subscribe_rate}%${f.discount ? ` ×${(f.discount * 10).toFixed(0)}折` : ""}`}
                </Td>
                <Td>
                  {f.can_buy == null ? "-"
                    : f.can_buy ? <span className="text-emerald-400">可买</span>
                    : <span className="text-zinc-500">暂停</span>}
                </Td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
        <p className="mt-3 text-[11px] text-zinc-600">
          「日累计限额」为天天基金展示的单账户单日累计申购上限；「限大额」表示开放申购但有上限；
          场外申购按未知价法，T 日 15:00 前按当日净值，QDII 净值一般 T+1 晚间披露。
        </p>
      </Card>

      <Card className="p-4">
        <SectionTitle title="限额风向" sub="每日快照自动对比，捕捉限购变化（放宽=绿，收紧=红）" />
        {data.events.length === 0 ? (
          <p className="py-8 text-center text-sm text-zinc-500">
            暂无变动记录——从部署第二天的每日快照开始积累
          </p>
        ) : (
          <ol className="space-y-2">
            {data.events.map((e, i) => {
              const numFrom = typeof e.from === "number";
              const loosened = numFrom ? (e.to as number) > (e.from as number)
                : (e.to as string ?? "").includes("开放") || (e.to as string ?? "").includes("限大额");
              return (
                <li key={i} className="flex flex-wrap items-baseline gap-x-2 rounded-lg border border-zinc-800/70 bg-zinc-950/50 px-3 py-2 text-sm">
                  <span className="num text-[11px] text-zinc-500">{e.date}</span>
                  <span className="text-zinc-200">{e.name}</span>
                  <span className="text-zinc-500">{e.field}</span>
                  <span className="num text-zinc-500">{e.from == null ? "无" : e.from}</span>
                  <span className="text-zinc-600">→</span>
                  <span className={`num font-medium ${loosened ? "text-emerald-400" : "text-rose-400"}`}>
                    {e.to == null ? "无" : e.to}
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </Card>
    </div>
  );
}
