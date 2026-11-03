"""每日更新与信号分析编排"""
from __future__ import annotations

import time
from datetime import datetime

import numpy as np
import pandas as pd

import fetchers
import storage
from backtest import run_backtest
from config import FUNDS, PE_MAX_AGE_HOURS
from indicators import enrich
from signals import compute_score, rating_of, score_series


def align_premium(enriched: pd.DataFrame, kline: pd.DataFrame) -> pd.Series | None:
    """按日期对齐 ETF 收盘价与净值，得到历史溢价率序列（%），与 enriched 行对齐"""
    if kline is None or kline.empty:
        return None
    m = enriched[["date", "nav"]].merge(kline[["date", "close"]], on="date", how="left")
    p = (m["close"] - m["nav"]) / m["nav"] * 100
    return pd.Series(p.to_numpy(), index=enriched.index)


def pe_pct_series(pe_df: pd.DataFrame, dates: pd.Series) -> pd.Series:
    """月度 PE 对齐到净值日期（ffill），再算历史百分位（只用当日及以前数据，避免未来函数）"""
    if pe_df is None or pe_df.empty:
        return pd.Series(np.nan, index=dates.index)
    s = pe_df.set_index("date")["pe"].sort_index()
    daily = s.reindex(pd.DatetimeIndex(dates), method="ffill")
    vals = daily.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if np.isnan(vals[i]):
            continue
        w = vals[: i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = (w <= vals[i]).mean() * 100
    return pd.Series(out, index=dates.index)


def get_pe_df(conn, max_age_hours: float = PE_MAX_AGE_HOURS) -> pd.DataFrame:
    """带缓存的标普500 PE 序列，最多每天抓一次"""
    cached_at = storage.get_cache(conn, "pe_fetched_at")
    if cached_at:
        try:
            age_h = (datetime.now() - datetime.fromisoformat(cached_at)).total_seconds() / 3600
        except ValueError:
            age_h = 1e9
        if age_h < max_age_hours:
            df = storage.load_pe(conn)
            if not df.empty:
                return df
    try:
        df = fetchers.fetch_sp500_pe()
        if not df.empty:
            storage.upsert_pe(conn, df)
            storage.set_cache(conn, "pe_fetched_at",
                              datetime.now().isoformat(timespec="seconds"))
            return df
    except Exception as e:  # noqa: BLE001
        print(f"[warn] multpl PE 抓取失败，使用缓存: {e}")
    return storage.load_pe(conn)


def _make_snapshot(fund, scored: pd.DataFrame, quote: dict | None) -> dict:
    row = scored.iloc[-1]
    nav = row["nav"]
    premium_close = row["premium"] if pd.notna(row["premium"]) else None
    premium_now = None
    if quote is not None and pd.notna(nav):
        premium_now = (quote["price"] - nav) / nav * 100
    premium_used = premium_now if premium_now is not None else premium_close
    # MACD 近 3 日金叉 +5 / 死叉 -5
    cross_up = (scored["dif"] > scored["dea"]) & (scored["dif"].shift(1) <= scored["dea"].shift(1))
    cross_dn = (scored["dif"] < scored["dea"]) & (scored["dif"].shift(1) >= scored["dea"].shift(1))
    bonus = 0.0
    if bool(cross_up.iloc[-3:].any()):
        bonus = 5.0
    elif bool(cross_dn.iloc[-3:].any()):
        bonus = -5.0
    score, dims = compute_score(
        premium=premium_used, rsi_v=row["rsi"], dd=row["dd60"],
        ma_dev=row["dev60"], pe_pct=row["pe_pct"], macd_bonus=bonus)

    def f(v, nd=4):
        return None if v is None or pd.isna(v) else round(float(v), nd)

    details = {
        "nav": f(nav), "nav_date": row["date"].strftime("%Y-%m-%d"),
        "pct": f(row.get("pct"), 2),
        "premium_close": f(premium_close, 2), "premium_now": f(premium_now, 2),
        "rsi": f(row["rsi"], 1), "dd60": f(row["dd60"], 1),
        "dev60": f(row["dev60"], 1), "dev250": f(row["dev250"], 1),
        "pe_pct": f(row["pe_pct"], 1), "macd_bonus": bonus,
        "dims": dims, "quote": quote,
    }
    return {"score": score, "rating": rating_of(score), "details": details}


def analyze_fund(conn, fund, pe_df: pd.DataFrame | None = None) -> dict | None:
    """从数据库读取数据 → 算指标/评分/回测，返回完整分析结果"""
    nav = storage.load_nav(conn, fund.code)
    if nav.empty or len(nav) < 35:
        return None
    enriched = enrich(nav)
    premium = None
    if fund.market:
        premium = align_premium(enriched, storage.load_kline(conn, fund.code))
    pe_pct = None
    if fund.index_name == "标普500" and pe_df is not None and not pe_df.empty:
        pe_pct = pe_pct_series(pe_df, enriched["date"])
    scored = score_series(enriched, premium, pe_pct)
    quote = None
    if fund.market:
        try:
            quote = fetchers.fetch_quote(fund.code, fund.market)
        except Exception:  # noqa: BLE001
            quote = None
    snapshot = _make_snapshot(fund, scored, quote)
    backtest = run_backtest(scored)
    return {"fund": fund, "scored": scored, "snapshot": snapshot,
            "backtest": backtest, "quote": quote}


def update_all(verbose: bool = True) -> None:
    """抓取全部基金数据并写入信号快照"""
    conn = storage.get_conn()
    pe_df = get_pe_df(conn)
    today = datetime.now().strftime("%Y-%m-%d")
    for fund in FUNDS:
        try:
            nav = fetchers.fetch_nav_history(fund.code)
            n1 = storage.upsert_nav(conn, fund.code, nav)
            n2 = 0
            if fund.market:
                kl = fetchers.fetch_kline(fund.code, fund.market)
                n2 = storage.upsert_kline(conn, fund.code, kl)
                time.sleep(0.2)
            if verbose:
                print(f"[fetch] {fund.code} {fund.name}: 净值 {n1} 条, K线 {n2} 条")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {fund.code} {fund.name} 抓取失败: {e}")
        res = analyze_fund(conn, fund, pe_df)
        if res is None:
            print(f"[warn] {fund.code} {fund.name} 数据不足，跳过")
            continue
        snap = res["snapshot"]
        storage.upsert_signal(conn, fund.code, today,
                              snap["score"], snap["rating"], snap["details"])
        if verbose:
            det = snap["details"]
            prem = det["premium_now"] if det["premium_now"] is not None else det["premium_close"]
            prem_s = f"{prem:+.2f}%" if prem is not None else "场外"
            print(f"[signal] {fund.name}: {snap['score']} {snap['rating']} "
                  f"净值 {det['nav']}({det['nav_date']}) 溢价 {prem_s} RSI {det['rsi']}")
    conn.close()


def refresh_if_stale(max_age_hours: float = 20) -> bool:
    """signals 表没有今天的数据时才联网更新（供 Streamlit 启动时调用）"""
    conn = storage.get_conn()
    latest = storage.latest_signal_date(conn)
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    if latest == today:
        return False
    update_all(verbose=True)
    return True
