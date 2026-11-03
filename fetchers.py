"""数据抓取：蛋卷净值 / 东财K线与实时行情 / multpl 标普500 PE
所有接口均已实测可用；失败时返回空 DataFrame/None，由上层降级处理
"""
from __future__ import annotations

import io
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


def fetch_kline(code: str, market: str, beg: str = "0") -> pd.DataFrame:
    """东财日K。fields2 顺序：日期,开,收,高,低,成交量(手),成交额,振幅"""
    secid = f"{1 if market == 'sh' else 0}.{code}"
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
