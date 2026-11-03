// 静态数据加载层：所有 JSON 由 GitHub Actions / 本机 update 脚本生成在 /data/ 下
import type { FundMeta, IndexData, Limits, Point2, Point4, Summary } from "./types";

const BASE = import.meta.env.BASE_URL; // 本地 "/"；Pages 上 "/nasdaq-signal/"

async function getJson<T>(rel: string): Promise<T> {
  const res = await fetch(`${BASE}data/${rel}`);
  if (!res.ok) throw new Error(`加载 ${rel} 失败: ${res.status}`);
  return res.json() as Promise<T>;
}

export const loadSummary = () => getJson<Summary>("summary.json");
export const loadLimits = () => getJson<Limits>("limits.json");
export const loadNav = (code: string) => getJson<Point2[]>(`nav/${code}.json`);
export const loadPremium = (code: string) => getJson<Point4[]>(`premium/${code}.json`);
export const loadIndex = (key: string) => getJson<IndexData>(`index/${key}.json`);
export const loadPe = () => getJson<Point2[]>("pe.json");

// ---- 派生集合 ----

export const marketFunds = (funds: Record<string, FundMeta>) =>
  Object.entries(funds).filter(([, f]) => f.market != null);

export const otcFunds = (funds: Record<string, FundMeta>) =>
  Object.entries(funds).filter(([, f]) => f.market == null);

export const INDEX_KEYS = [
  { key: "ndx", label: "纳指综合(1991-)" },
  { key: "spx", label: "标普500(1986-)" },
  { key: "ndx100", label: "纳指100(2019-)" },
] as const;
