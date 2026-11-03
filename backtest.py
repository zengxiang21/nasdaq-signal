"""历史胜率回测（通用规则引擎）
对任意价格序列（基金净值 / 指数收盘）按规则筛选买入日，统计持有 N 个交易日后的
胜率 / 平均收益 / 盈亏比。web 前端有同口径 TS 实现（web/src/lib/backtest.ts），
改动规则时两边要同步。
"""
from __future__ import annotations

import pandas as pd

from config import BACKTEST_HORIZONS


def win_stats(close: pd.Series, mask: pd.Series,
              horizons=BACKTEST_HORIZONS) -> dict:
    """mask=True 的日子买入，持有 h 天的收益统计"""
    fwd = {h: close.shift(-h) / close - 1 for h in horizons}
    out = {}
    for h in horizons:
        rets = fwd[h][mask].dropna()
        if len(rets) == 0:
            out[h] = {"n": 0, "win_rate": None, "avg": None, "median": None,
                      "profit_factor": None}
            continue
        gains = rets[rets > 0]
        losses = rets[rets <= 0]
        avg_loss = abs(float(losses.mean())) if len(losses) else None
        out[h] = {
            "n": int(len(rets)),
            "win_rate": round(float((rets > 0).mean() * 100), 1),
            "avg": round(float(rets.mean()) * 100, 2),
            "median": round(float(rets.median()) * 100, 2),
            "profit_factor": (round(float(gains.mean()) / avg_loss, 2)
                              if avg_loss and len(gains) else None),
        }
    return out


def down_streak(close: pd.Series) -> pd.Series:
    """连续下跌天数（当日收跌则 +1，否则清零）"""
    chg = close.diff() < 0
    streak = pd.Series(0, index=close.index, dtype=float)
    run = 0.0
    for i, v in enumerate(chg):
        run = run + 1 if v else 0.0
        streak.iloc[i] = run
    return streak


def build_rules(df: pd.DataFrame, with_premium: bool = False) -> dict[str, pd.Series]:
    """由 enriched 指标列构造规则集。df 需以 DatetimeIndex 为索引，
    含 nav/rsi/dd60/dev60（及可选 premium）"""
    close = df["nav"]
    rules: dict[str, pd.Series] = {
        "星期一买入": pd.Series(df.index.weekday == 0, index=df.index),
        "星期五买入": pd.Series(df.index.weekday == 4, index=df.index),
        "连跌2天": down_streak(close) >= 2,
        "连跌3天": down_streak(close) >= 3,
        "单日跌超1.5%": close.pct_change() <= -0.015,
        "单日跌超2.5%": close.pct_change() <= -0.025,
        "低于MA20超3%": ((close - close.rolling(20).mean()) / close.rolling(20).mean()
                         <= -0.03),
        "低于MA60超8%": df["dev60"] <= -8,
        "RSI<30": df["rsi"] < 30,
        "RSI<40": df["rsi"] < 40,
        "60日回撤≥10%": df["dd60"] <= -10,
        "60日回撤≥15%": df["dd60"] <= -15,
    }
    if with_premium:
        rules["溢价≤1%(仅场内)"] = df["premium"] <= 1
        rules["溢价≤3%(仅场内)"] = df["premium"] <= 3
    return {k: v.fillna(False).astype(bool) for k, v in rules.items()}


def run_rule_backtest(close: pd.Series, rules: dict[str, pd.Series],
                      horizons=BACKTEST_HORIZONS,
                      with_benchmark: bool = True) -> list[dict]:
    """返回 [{rule, stats}, ...]，末尾附基准"""
    results = [{"rule": name, "stats": win_stats(close, mask, horizons)}
               for name, mask in rules.items()]
    if with_benchmark:
        results.append({"rule": "基准：任意一天买入",
                        "stats": win_stats(close, pd.Series(True, index=close.index),
                                           horizons)})
    return results


def run_backtest(scored_df: pd.DataFrame) -> list[dict]:
    """对若干经典规则 + 综合评分规则回测，返回 [{rule, stats}, ...]（兼容旧接口）"""
    d = scored_df.dropna(subset=["nav"]).set_index("date").sort_index()
    rules = build_rules(d, with_premium="premium" in d.columns)
    rules["评分≥70"] = (d["score"] >= 70).fillna(False).astype(bool)
    rules["评分≥80"] = (d["score"] >= 80).fillna(False).astype(bool)
    return run_rule_backtest(d["nav"], rules)


def backtest_to_df(results: list[dict]) -> pd.DataFrame:
    """回测结果转展示用 DataFrame"""
    rows = []
    for r in results:
        row = {"规则": r["rule"]}
        for h, s in r["stats"].items():
            if s["n"] == 0:
                row[f"{h}日胜率"] = "-"
                row[f"{h}日均收益"] = "-"
            else:
                row[f"{h}日胜率"] = f"{s['win_rate']:.1f}% (n={s['n']})"
                row[f"{h}日均收益"] = f"{s['avg']:+.2f}%"
        rows.append(row)
    return pd.DataFrame(rows)
