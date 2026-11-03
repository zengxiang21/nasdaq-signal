"""一次性数据源探针：确定基金池真实代码、限额/费率最佳抓取口
只跑一次用于构建 config，不属于日常管线。
"""
from __future__ import annotations

import io
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import requests

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Referer": "https://fund.eastmoney.com/",
}


def get(url: str, timeout: float = 15) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r


def probe_search(key: str) -> None:
    print(f"\n===== FundSearchAPI: {key} =====")
    r = get(f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={key}")
    data = json.loads(r.text)
    for item in (data.get("Datas") or [])[:40]:
        base = item.get("FundBaseInfo") or {}
        print(f"{base.get('FCODE')}  {base.get('SHORTNAME')}  "
              f"[{base.get('FUNDTYPE')}]  净值{base.get('FSRQ')}")


def probe_mobapi(code: str) -> None:
    print(f"\n===== fundmobapi FundMNDetailInformation {code} =====")
    url = ("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNDetailInformation"
           f"?FCODE={code}&deviceid=Wap&plat=Wap&product=EFund&version=6.2.8")
    try:
        d = json.loads(get(url).text).get("Expansion") or {}
        keys = ["FCODE", "SHORTNAME", "SGZT", "SHZT", "MINSG", "MAXSG", "MINSH",
                "BUY", "SOP", "JJGSID", "FSRQ", "DWJZ"]
        for k in keys:
            print(f"  {k}: {d.get(k)}")
    except Exception as e:  # noqa: BLE001
        print(f"  失败: {e}")


def probe_f10(code: str) -> None:
    print(f"\n===== fundf10 jjfl {code} =====")
    r = get(f"http://fundf10.eastmoney.com/jjfl_{code}.html")
    html = r.text
    for label in ("申购状态", "赎回状态", "日累计申购限额", "首次购买", "追加购买"):
        m = re.search(label + r"</td>\s*<td[^>]*>([^<]+)", html)
        print(f"  {label}: {m.group(1).strip() if m else '未匹配'}")
    # 限额可能以其他形式出现
    for m in re.finditer(r"(单日|日累计|累计)(申购)?(购买|申购)?(上限|限额)[^<]*?([\d.]+)\s*元", html):
        print(f"  限额片段: {m.group(0)}")


def probe_danjuan(code: str) -> None:
    print(f"\n===== danjuan djapi/fund {code} =====")
    try:
        r = get(f"https://danjuanfunds.com/djapi/fund/{code}",
                ) if False else requests.get(
            f"https://danjuanfunds.com/djapi/fund/{code}",
            headers={"User-Agent": UA["User-Agent"], "Referer": "https://danjuanfunds.com/"},
            timeout=15)
        j = json.loads(r.text)
        d = j.get("data") or {}
        fd = d.get("fund_derived") or {}
        print(f"  name: {d.get('fd_name')}  subscribe_status: {d.get('subscribe_status')}"
              f"  can_buy: {d.get('can_buy')}  auto_invest: {d.get('auto_invest_status')}")
        print(f"  净值: {fd.get('unit_nav')} @ {fd.get('nav_date')}  年化: {fd.get('best-established')}")
        print(f"  年度收益条数: {len(d.get('annual_performance_list') or [])}")
    except Exception as e:  # noqa: BLE001
        print(f"  失败: {e}")


def probe_kline_requests() -> None:
    print("\n===== push2his from requests =====")
    for secid, label in (("100.SPX", "标普500"), ("100.NDX", "纳指综合"),
                         ("100.NDX100", "纳指100"), ("1.513100", "纳指ETF国泰"),
                         ("0.159941", "纳指ETF广发")):
        try:
            url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
                   f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
                   "&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
                   "&klt=101&fqt=1&beg=19800101&end=20500101")
            d = json.loads(get(url).text).get("data") or {}
            k = d.get("klines") or []
            print(f"  {secid} {d.get('name')}: {len(k)} 根  "
                  f"{k[0].split(',')[0] if k else '-'} ~ {k[-1].split(',')[0] if k else '-'}")
        except Exception as e:  # noqa: BLE001
            print(f"  {secid} 失败: {e}")


def probe_tencent_quote() -> None:
    print("\n===== 腾讯实时行情 from requests =====")
    try:
        r = requests.get("https://qt.gtimg.cn/q=sh513100,usIXIC,whUSDCNY",
                         headers={"User-Agent": UA["User-Agent"]}, timeout=10)
        r.encoding = "gbk"
        for line in r.text.strip().split("\n"):
            print(" ", line[:120])
    except Exception as e:  # noqa: BLE001
        print(f"  失败: {e}")


if __name__ == "__main__":
    probe_search("纳斯达克100")
    probe_search("标普500")
    probe_mobapi("270042")
    probe_mobapi("050025")
    probe_f10("270042")
    probe_f10("050025")
    probe_danjuan("513100")
    probe_danjuan("270042")
    probe_kline_requests()
    probe_tencent_quote()
