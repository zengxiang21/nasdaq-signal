// 浏览器直连腾讯行情（CORS *），把静态站的场内溢价升级为实时
// 口径：场内最新价 vs 最新披露净值（QDII 净值为 T-1 美股收盘口径，见「说明」页）
export interface TencentQuote {
  code: string;
  name: string;
  price: number;
}

export async function fetchTencentQuotes(
  tencentCodes: string[],
): Promise<Record<string, TencentQuote>> {
  if (tencentCodes.length === 0) return {};
  const res = await fetch(`https://qt.gtimg.cn/q=${tencentCodes.join(",")}`);
  if (!res.ok) throw new Error("腾讯行情请求失败");
  // 响应为 GBK，需手动解码
  const buf = await res.arrayBuffer();
  const text = new TextDecoder("gbk").decode(buf);
  const out: Record<string, TencentQuote> = {};
  for (const m of text.matchAll(/v_(\w+)="([^"]*)"/g)) {
    const parts = m[2].split("~");
    const price = Number(parts[3]);
    if (parts.length > 5 && Number.isFinite(price)) {
      // 腾讯返回 sh513100 / sz159941 形式，去掉市场前缀统一用 6 位代码作 key
      out[m[1].replace(/^(sh|sz)/, "")] = { code: m[1], name: parts[1], price };
    }
  }
  return out;
}

export const toTencentCode = (code: string, market: string | null): string | null =>
  market === "sh" ? `sh${code}` : market === "sz" ? `sz${code}` : null;
