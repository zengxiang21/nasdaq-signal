import type { ReactNode } from "react";

// ---- 基础容器 ----
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-zinc-800 bg-zinc-900/60 ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
      {sub && <p className="mt-0.5 text-xs text-zinc-500">{sub}</p>}
    </div>
  );
}

export function Loading({ text = "加载中…" }: { text?: string }) {
  return <div className="py-24 text-center text-sm text-zinc-500">{text}</div>;
}

export function ErrorBlock({ msg }: { msg: string }) {
  return (
    <div className="mx-auto my-24 max-w-md rounded-xl border border-red-900/50 bg-red-950/30 p-6 text-center">
      <p className="text-red-400">{msg}</p>
      <p className="mt-2 text-xs text-zinc-500">先在项目根目录跑 <code>python scripts/export_web_data.py</code> 生成数据</p>
    </div>
  );
}

// ---- 数字格式 ----
export const fmtPct = (v: number | null | undefined, nd = 2, sign = true) =>
  v == null ? "-" : `${sign && v > 0 ? "+" : ""}${v.toFixed(nd)}%`;

export const fmtNum = (v: number | null | undefined, nd = 2) =>
  v == null ? "-" : v.toFixed(nd);

// ---- 评级 ----
export const RATING_STYLES: Record<string, string> = {
  "🟢 买入区": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  "🟡 观望/定投区": "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "🔴 高估谨慎": "bg-red-500/15 text-red-400 border-red-500/30",
  "🚫 溢价高危": "bg-rose-600/20 text-rose-400 border-rose-600/40",
  "⚪ 数据不足": "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
};

export function RatingBadge({ rating, className = "" }: { rating: string; className?: string }) {
  return (
    <span className={`num inline-block rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${RATING_STYLES[rating] ?? RATING_STYLES["⚪ 数据不足"]} ${className}`}>
      {rating}
    </span>
  );
}

// 溢价色阶：<=0 折价 / <=1 低 / <=3 警惕 / <=5 偏高 / <=10 高 / >10 高危
export function premColor(p: number | null | undefined): string {
  if (p == null) return "text-zinc-500";
  if (p <= 0) return "text-emerald-400";
  if (p <= 1) return "text-lime-400";
  if (p <= 3) return "text-amber-400";
  if (p <= 5) return "text-orange-400";
  if (p <= 10) return "text-red-400";
  return "text-rose-500 font-semibold";
}

export function PremText({ v, nd = 2 }: { v: number | null | undefined; nd?: number }) {
  return <span className={`num ${premColor(v)}`}>{fmtPct(v, nd)}</span>;
}

// 申购状态
export function StatusChip({ status, limit }: { status: string | null; limit: number | null }) {
  if (!status) return <span className="text-zinc-500">-</span>;
  const paused = status.includes("暂停") || status.includes("关闭");
  const cls = paused
    ? "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
    : status.includes("限大额")
      ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
      : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  const limitText = limit != null ? ` ${limit >= 10000 ? `${limit / 10000}万` : limit}元/日` : "";
  return (
    <span className={`num inline-block rounded-md border px-2 py-0.5 text-xs whitespace-nowrap ${cls}`}>
      {status}{limitText}
    </span>
  );
}

// ---- 表格骨架（横向滚动 + 斑马纹弱化） ----
export function TableWrap({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-1 overflow-x-auto px-1 pb-1">
      <table className="w-full min-w-[640px] border-collapse text-sm">{children}</table>
    </div>
  );
}

export function Th({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return (
    <th className={`border-b border-zinc-800 px-3 py-2 text-left text-xs font-medium text-zinc-500 whitespace-nowrap ${className}`}>
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`num border-b border-zinc-800/60 px-3 py-2 whitespace-nowrap ${className}`}>
      {children}
    </td>
  );
}
