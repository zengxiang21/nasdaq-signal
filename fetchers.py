"""数据抓取：蛋卷净值/详情 / 东财K线与实时行情 / 东财F10限额费率 / multpl 标普500 PE
所有接口均已实测可用；失败时返回空 DataFrame/None，由上层降级处理
"""
from __future__ import annotations

import io
import json
import re
import time

import pandas as pd
import requests

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Referer": "https://danjuanfunds.com/",
}
TIMEOUT = 15
_EMPTY_NAV = pd.DataFrame(columns=["date", "nav", "pct"])
_EMPTY_KLINE = pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume", "amount"])


def _get(url: str, headers: dict | None = None, retries: int = 2) -> requests.Response:
    last: Exception | None = None
    for i in range(retries + 1):
        try:
            r = requests.get(url, headers=headers or UA, timeout=TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.5 * (i + 1))
    raise last  # type: ignore[misc]


def fetch_nav_history(code: str, pages: int = 5, size: int = 200) -> pd.DataFrame:
    """蛋卷基金历史净值（page=1 为最新，倒序分页）"""
    rows: list[dict] = []
    for page in range(1, pages + 1):
        url = (f"https://danjuanfunds.com/djapi/fund/nav/history/{code}"
               f"?size={size}&page={page}")
        try:
            payload = _get(url).json()
        except Exception:
            break
        items = (payload.get("data") or {}).get("items") or []
        if not items:
            break
        rows.extend(items)
        if len(items) < size:
            break
        time.sleep(0.25)
    if not rows:
        return _EMPTY_NAV.copy()
    df = pd.DataFrame(rows)[["date", "nav", "percentage"]].rename(columns={"percentage": "pct"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df["pct"] = pd.to_numeric(df["pct"], errors="coerce")
    return (df.dropna(subset=["date", "nav"])
              .drop_duplicates(subset="date")
              .sort_values("date")
              .reset_index(drop=True))


def fetch_kline_secid(secid: str, beg: str = "0") -> pd.DataFrame:
    """东财日K（直接指定 secid，如 100.SPX / 1.513100）。
    fields2 顺序：日期,开,收,高,低,成交量(手),成交额,振幅"""
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
           "&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
           f"&klt=101&fqt=1&beg={beg}&end=20500101")
    try:
        data = _get(url).json().get("data") or {}
    except Exception:
        return _EMPTY_KLINE.copy()
    klines = data.get("klines") or []
    if not klines:
        return _EMPTY_KLINE.copy()
    df = pd.DataFrame([k.split(",") for k in klines],
                      columns=["date", "open", "close", "high", "low",
                               "volume", "amount", "amp"])
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "close", "high", "low", "volume", "amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return (df.dropna(subset=["date", "close"])
              .sort_values("date").reset_index(drop=True))


def fetch_kline(code: str, market: str, beg: str = "0") -> pd.DataFrame:
    """东财日K（场内基金代码版）"""
    secid = f"{1 if market == 'sh' else 0}.{code}"
    return fetch_kline_secid(secid, beg=beg)


def fetch_quote(code: str, market: str) -> dict | None:
    """东财实时行情（盘后即收盘价）"""
    secid = f"{1 if market == 'sh' else 0}.{code}"
    url = ("https://push2.eastmoney.com/api/qt/stock/get"
           f"?secid={secid}&fields=f43,f57,f58,f59,f60,f86,f170")
    try:
        d = _get(url).json().get("data") or {}
    except Exception:
        return None
    if not d or d.get("f43") in (None, "-"):
        return None
    decimals = int(d.get("f59") or 3)
    return {
        "code": code,
        "name": d.get("f58"),
        "price": d["f43"] / (10 ** decimals),
        "pct": (d.get("f170") or 0) / 100.0,
        "ts": d.get("f86"),
    }


def fetch_sp500_pe() -> pd.DataFrame:
    """multpl 标普500 PE 月度序列（Date, Value 两列，1871 至今）"""
    url = "https://www.multpl.com/s-p-500-pe-ratio/table/by-month"
    r = _get(url)
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[0].copy()
    df.columns = ["date", "pe"]
    df["date"] = (df["date"].astype(str)
                  .str.replace("†", "", regex=False)
                  .str.replace("Estimate", "", regex=False)
                  .str.strip())
    df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna().sort_values("date").reset_index(drop=True)


# ---------- F10 限额与费率（天天基金 fundf10，HTML 解析） ----------

def _f10_cell(html: str, label: str) -> str | None:
    """取 <td>label</td><td>value</td> 模式的单元格值"""
    m = re.search(re.escape(label) + r"</td>\s*<td[^>]*>([^<]+)", html)
    if not m:
        return None
    return m.group(1).strip()


def _parse_limit_yuan(text: str | None) -> float | None:
    """"100.00元" / "10.00元" → 100.0；暂停/无限额 → None"""
    if not text:
        return None
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*元", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def fetch_f10_fee(code: str) -> dict | None:
    """天天基金 F10 费率页：申购状态/赎回状态/日累计申购限额/起购金额/申购费率。
    ETF 也可能无申购状态字段（一级市场申赎口径），缺失时对应键为 None。"""
    url = f"http://fundf10.eastmoney.com/jjfl_{code}.html"
    try:
        r = _get(url)
    except Exception:
        return None
    html = r.text
    if "基金费率" not in html and "申购状态" not in html:
        return None
    status_buy = _f10_cell(html, "申购状态")
    status_redeem = _f10_cell(html, "赎回状态")
    daily_limit_raw = _f10_cell(html, "日累计申购限额")
    min_buy_raw = _f10_cell(html, "首次购买")
    # 申购费率：表格首档（小于100万元）原价
    m = re.search(r"小于100万元?</td>\s*<td[^>]*>([\d.]+)%", html)
    rate = float(m.group(1)) if m else None
    return {
        "status_buy": status_buy,
        "status_redeem": status_redeem,
        "daily_limit": _parse_limit_yuan(daily_limit_raw),
        "daily_limit_text": daily_limit_raw,
        "min_buy": _parse_limit_yuan(min_buy_raw),
        "subscribe_rate": rate,
    }


# ---------- 蛋卷基金详情（仅场外基金有数据） ----------

def fetch_dj_detail(code: str) -> dict | None:
    """蛋卷基金详情：申购/赎回/定投状态、can_buy、费率、年度业绩"""
    url = f"https://danjuanfunds.com/djapi/fund/{code}"
    try:
        data = _get(url).json().get("data") or {}
    except Exception:
        return None
    if not data:
        return None
    rates = data.get("fund_rates") or {}
    derived = data.get("fund_derived") or {}
    return {
        "name": data.get("fd_name"),
        "subscribe_status": data.get("subscribe_status"),   # "0"=不可申购
        "withdraw_status": data.get("withdraw_status"),     # "1"=可赎回
        "auto_invest_status": data.get("auto_invest_status"),
        "can_buy": data.get("can_buy"),
        "type_desc": data.get("type_desc"),
        "subscribe_rate": rates.get("subscribe_rate"),
        "declare_rate": rates.get("declare_rate"),
        "discount": rates.get("discount"),
        "unit_nav": derived.get("unit_nav"),
        "nav_date": derived.get("nav_date"),
    }


# ---------- 腾讯实时行情（浏览器端也可直连，此处供 Python 端兜底） ----------

def fetch_tencent_quotes(codes: list[str]) -> dict[str, dict]:
    """qt.gtimg.cn 实时行情，返回 {code: {price, pct, name}}。codes 如 ["sh513100"]"""
    out: dict[str, dict] = {}
    if not codes:
        return out
    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    try:
        r = requests.get(url, headers={"User-Agent": UA["User-Agent"]}, timeout=10)
        r.encoding = "gbk"
    except Exception:
        return out
    for line in r.text.strip().split("\n"):
        m = re.match(r'v_(\w+)="([^"]*)"', line)
        if not m:
            continue
        parts = m.group(2).split("~")
        if len(parts) < 6:
            continue
        try:
            out[m.group(1)] = {
                "name": parts[1],
                "price": float(parts[3]),
                "pct": float(parts[32]) if len(parts) > 32 and parts[32] else 0.0,
            }
        except (ValueError, IndexError):
            continue
    return out
