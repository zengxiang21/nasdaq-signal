"""导出 web 静态站所需的全部 JSON 数据到 web/public/data/
用法：
  python scripts/export_web_data.py            # 只用库里已有数据导出
  python scripts/export_web_data.py --update   # 先跑一轮 update_all 再导出（每日任务用）

产物：
  summary.json        总览：温度计 + 每只基金评分卡
  funds.json          基金池静态配置
  nav/{code}.json     净值历史 [[date, nav], ...]
  premium/{code}.json 场内溢价历史 [[date, close, nav, prem%], ...]
  index/{key}.json    指数长历史 {name, since, note?, points: [[date, close], ...]}
  limits.json         场外限额现状 + 限额风向事件流
  pe.json             标普500 PE 月度 [[date, pe], ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import fetchers  # noqa: E402
import pipeline  # noqa: E402
import storage  # noqa: E402
from config import (FUNDS, INDEXES, TEMP_CROWD_WEIGHT, TEMP_PREMIUM_WEIGHT,  # noqa: E402
                    WEB_DATA_DIR)
from signals import rating_of, score_premium  # noqa: E402


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    print(f"  [write] {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")


def _f(v, nd=2):
    """NaN/None → None，其余保留 nd 位"""
    if v is None:
        return None
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return round(float(v), nd)


def collect_funds(conn) -> dict:
    """汇总每只基金的评分卡/净值/溢价/限额，返回前端 funds 字典"""
    pe_df = pipeline.get_pe_df(conn)
    today = datetime.now().strftime("%Y-%m-%d")
    funds: dict[str, dict] = {}

    # 场外限额与蛋卷状态
    for fund in FUNDS:
        info = {}
        if fund.kind == "otc":
            f10 = fetchers.fetch_f10_fee(fund.code) or {}
            dj = fetchers.fetch_dj_detail(fund.code) or {}
            info = {**f10, "dj_status": dj.get("subscribe_status"),
                    "can_buy": dj.get("can_buy"),
                    "dj_name": dj.get("name"),
                    "subscribe_rate_dj": dj.get("subscribe_rate"),
                    "discount": dj.get("discount"),
                    "declare_rate": dj.get("declare_rate")}
            storage.upsert_fund_limits(conn, fund.code, today, info)
            print(f"  [limits] {fund.code} {fund.name}: "
                  f"{info.get('status_buy')} / 限额 {info.get('daily_limit')} 元")
        funds[fund.code] = {"_info": info}

    # 每只基金的评分卡
    for fund in FUNDS:
        nav = storage.load_nav(conn, fund.code)
        if nav.empty or len(nav) < 35:
            print(f"  [warn] {fund.code} {fund.name}: 净值不足，跳过评分")
            funds[fund.code]["_card"] = None
            continue
        enriched = pipeline.enrich(nav)
        premium_hist = None
        if fund.on_market:
            premium_hist = pipeline.align_premium(enriched,
                                                  storage.load_kline(conn, fund.code))
        pe_pct = None
        if fund.index_name == "标普500" and not pe_df.empty:
            pe_pct = pipeline.pe_pct_series(pe_df, enriched["date"])
        scored = pipeline.score_series(enriched, premium_hist, pe_pct)
        quote = None
        if fund.on_market:
            try:
                quote = fetchers.fetch_quote(fund.code, fund.market)
            except Exception:  # noqa: BLE001
                quote = None
        snap = pipeline._make_snapshot(fund, scored, quote)
        row = scored.iloc[-1]
        funds[fund.code]["_card"] = {
            "score": snap["score"], "rating": snap["rating"],
            "nav": _f(row["nav"], 4), "nav_date": row["date"].strftime("%Y-%m-%d"),
            "pct": _f(row.get("pct"), 2),
            "rsi": _f(row["rsi"], 1), "dd60": _f(row["dd60"], 1),
            "dev60": _f(row["dev60"], 1),
            "pe_pct": _f(row["pe_pct"], 1),
            "premium_now": snap["details"]["premium_now"],
            "premium_close": snap["details"]["premium_close"],
            "premium_veto": snap["details"]["premium_now"] is not None
                            and snap["details"]["premium_now"] >= 10,
        }
        print(f"  [card] {fund.name}: {snap['score']} {snap['rating']}")
    return funds


def build_temperature(funds: dict) -> dict:
    """QDII 贪婪温度计 = 100 - (0.6×溢价便宜分 + 0.4×限购宽松分)
    温度越高 = 溢价越贵 + 限购越拥挤 = 市场越过热"""
    prem_list = [c["premium_now"] if c["premium_now"] is not None
                 else c["premium_close"]
                 for c in (f.get("_card") for f in funds.values())
                 if c and (c["premium_now"] is not None
                           or c["premium_close"] is not None)]
    prem_median = float(np.median(prem_list)) if prem_list else None
    prem_score = score_premium(prem_median) if prem_median is not None else None

    otc = [(f["_info"], f.get("_card")) for f in funds.values()
           if f["_info"] and f.get("_card")]
    total = len(otc)
    crowded = sum(1 for info, _ in otc
                  if (info.get("daily_limit") is None
                      and "暂停" in (info.get("status_buy") or ""))
                  or (info.get("daily_limit") is not None
                      and info["daily_limit"] <= 100))
    crowd_ratio = crowded / total if total else None
    crowd_score = (1 - crowd_ratio) * 100 if crowd_ratio is not None else None

    parts = [p for p in (prem_score, crowd_score) if p is not None]
    opportunity = (TEMP_PREMIUM_WEIGHT * prem_score
                   + TEMP_CROWD_WEIGHT * crowd_score) if len(parts) == 2 else (
        parts[0] if parts else None)
    temp = 100 - opportunity if opportunity is not None else None
    level = ("过热" if temp is not None and temp >= 70 else
             "偏热" if temp is not None and temp >= 45 else
             "中性" if temp is not None and temp >= 25 else "冰点")
    return {"temp": _f(temp, 1), "level": level,
            "premium_median": _f(prem_median, 2),
            "premium_score": _f(prem_score, 1),
            "crowd_ratio": _f(crowd_ratio * 100, 1) if crowd_ratio is not None else None,
            "crowd_score": _f(crowd_score, 1),
            "n_market": len(prem_list), "n_otc": total}


def build_limits(conn, funds: dict) -> dict:
    """场外限额现状 + 由历史快照 diff 出的限额风向事件"""
    out_funds, events = [], []
    for fund in FUNDS:
        if fund.kind != "otc":
            continue
        info = funds[fund.code]["_info"]
        hist = storage.load_fund_limits(conn, fund.code)
        entry = {"code": fund.code, "name": fund.name, "share": fund.share,
                 "index_name": fund.index_name,
                 "status_buy": info.get("status_buy"),
                 "status_redeem": info.get("status_redeem"),
                 "daily_limit": info.get("daily_limit"),
                 "min_buy": info.get("min_buy"),
                 "subscribe_rate": info.get("subscribe_rate"),
                 "discount": info.get("discount"),
                 "can_buy": info.get("can_buy")}
        out_funds.append(entry)
        # diff：最近两次快照
        if len(hist) >= 2:
            prev, curr = hist[-2], hist[-1]
            if prev["status_buy"] != curr["status_buy"]:
                events.append({"date": curr["date"], "code": fund.code,
                               "name": fund.name, "field": "申购状态",
                               "from": prev["status_buy"], "to": curr["status_buy"]})
            if prev["daily_limit"] != curr["daily_limit"]:
                events.append({"date": curr["date"], "code": fund.code,
                               "name": fund.name, "field": "日累计限额",
                               "from": prev["daily_limit"], "to": curr["daily_limit"]})
    events.sort(key=lambda e: e["date"], reverse=True)
    return {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "funds": out_funds, "events": events[:50]}


def export_static(conn, funds: dict) -> None:
    out = Path(WEB_DATA_DIR)
    print("== 导出 JSON ==")

    funds_meta = {f.code: {"name": f.name, "kind": f.kind, "market": f.market,
                           "index_name": f.index_name, "share": f.share}
                  for f in FUNDS}

    # summary + funds
    summary_funds = {}
    for f in FUNDS:
        card = funds[f.code].get("_card")
        info = funds[f.code]["_info"]
        summary_funds[f.code] = {**funds_meta[f.code], "card": card,
                                 "limits": {k: info.get(k) for k in
                                            ("status_buy", "daily_limit", "min_buy",
                                             "subscribe_rate")}
                                 if info else None}
    temp = build_temperature(funds)
    _dump(out / "summary.json", {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "temperature": temp, "funds": summary_funds,
    })
    _dump(out / "funds.json", funds_meta)

    # 净值与溢价历史
    for f in FUNDS:
        nav = storage.load_nav(conn, f.code)
        if not nav.empty:
            _dump(out / "nav" / f"{f.code}.json",
                  [[d.strftime("%Y-%m-%d"), _f(n, 4)]
                   for d, n in zip(nav["date"], nav["nav"])])
        if f.on_market:
            kl = storage.load_kline(conn, f.code)
            if not kl.empty and not nav.empty:
                m = nav[["date", "nav"]].merge(kl[["date", "close"]], on="date",
                                               how="inner")
                _dump(out / "premium" / f"{f.code}.json",
                      [[d.strftime("%Y-%m-%d"), _f(c, 4), _f(n, 4),
                        _f((c - n) / n * 100, 2)]
                       for d, n, c in zip(m["date"], m["nav"], m["close"])])

    # 指数长历史
    for key, meta in INDEXES.items():
        secid = meta["secid"]
        kl = fetchers.fetch_kline_secid(secid)
        if kl.empty:
            kl = storage.load_kline(conn, secid)
            if kl.empty:
                print(f"  [warn] 指数 {key} 无数据")
                continue
        else:
            storage.upsert_kline(conn, secid, kl)
        payload = {"name": meta["name"], "since": meta["since"],
                   "points": [[d.strftime("%Y-%m-%d"), _f(c, 2)]
                              for d, c in zip(kl["date"], kl["close"])]}
        if meta.get("note"):
            payload["note"] = meta["note"]
        _dump(out / "index" / f"{key}.json", payload)
        print(f"  [index] {key}: {len(kl)} 根")

    # 标普 PE
    pe_df = storage.load_pe(conn)
    if not pe_df.empty:
        _dump(out / "pe.json",
              [[d.strftime("%Y-%m-%d"), _f(v, 2)]
               for d, v in zip(pe_df["date"], pe_df["pe"])])

    # 限额
    _dump(out / "limits.json", build_limits(conn, funds))


def main() -> None:
    ap = argparse.ArgumentParser(description="导出 web 静态数据")
    ap.add_argument("--update", action="store_true", help="先跑一轮数据更新")
    args = ap.parse_args()

    if args.update:
        print("== 更新数据 ==")
        pipeline.update_all(verbose=True)

    conn = storage.get_conn()
    try:
        funds = collect_funds(conn)
        export_static(conn, funds)
    finally:
        conn.close()
    print("== 导出完成 ==")


if __name__ == "__main__":
    main()
