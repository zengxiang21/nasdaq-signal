"""历史胜率回测：信号触发日买入，持有 N 个交易日后的盈利概率"""
from __future__ import annotations

import pandas as pd

from config import BACKTEST_HORIZONS


def _win_stats(nav: pd.Series, mask: pd.Series,
               horizons=BACKTEST_HORIZONS) -> dict:
    out = {}
    for h in horizons:
        fwd = nav.shift(-h) / nav - 1
        rets = fwd[mask].dropna()
        if len(rets) == 0:
            out[h] = {"n": 0, "win_rate": None, "avg": None, "median": None}
        else:
            out[h] = {
                "n": int(len(rets)),
                "win_rate": round(float((rets > 0).mean() * 100), 1),
                "avg": round(float(rets.mean() * 100), 2),
                "median": round(float(rets.median() * 100), 2),
            }
    return out


def run_backtest(scored_df: pd.DataFrame) -> list[dict]:
    """对若干经典规则 + 综合评分规则回测，返回 [{rule, stats}, ...]"""
    d = scored_df.dropna(subset=["nav"]).set_index("date").sort_index()
    nav = d["nav"]
    rules = {
        "RSI<30": d["rsi"] < 30,
        "RSI<40": d["rsi"] < 40,
        "回撤≥10%": d["dd60"] <= -10,
        "回撤≥15%": d["dd60"] <= -15,
        "低于MA60超8%": d["dev60"] <= -8,
        "溢价≤1%(仅场内)": d["premium"] <= 1,
        "评分≥70": d["score"] >= 70,
        "评分≥80": d["score"] >= 80,
    }
    results = []
    for name, mask in rules.items():
        results.append({"rule": name,
                        "stats": _win_stats(nav, mask.fillna(False).astype(bool))})
    results.append({"rule": "基准：任意一天买入",
                    "stats": _win_stats(nav, pd.Series(True, index=d.index))})
    return results


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
