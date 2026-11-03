"""信号评分引擎：五个维度线性打分 + 加权合成 0-100 综合评分"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import BUY_THRESHOLD, PREMIUM_VETO, WATCH_THRESHOLD, WEIGHTS


def _lerp(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    """分段线性插值，超出范围截断到端点"""
    if x0 == x1:
        return y0
    t = max(0.0, min(1.0, (x - x0) / (x1 - x0)))
    return y0 + t * (y1 - y0)


def score_premium(p) -> float:
    """溢价率(%) → 分数。溢价越低越便宜"""
    if p is None or pd.isna(p):
        return np.nan
    if p <= 0:
        return 100.0                      # 折价：最便宜
    if p <= 1:
        return _lerp(p, 0, 100, 1, 80)
    if p <= 3:
        return _lerp(p, 1, 80, 3, 50)
    if p <= 5:
        return _lerp(p, 3, 50, 5, 20)
    return max(0.0, _lerp(p, 5, 20, 10, 0))  # 溢价 10%+ 基本接盘


def score_rsi(r) -> float:
    """RSI → 分数。超卖高分"""
    if r is None or pd.isna(r):
        return np.nan
    if r <= 20:
        return 100.0
    if r <= 30:
        return _lerp(r, 20, 100, 30, 80)
    if r <= 50:
        return _lerp(r, 30, 80, 50, 50)
    if r <= 70:
        return _lerp(r, 50, 50, 70, 20)
    return max(0.0, _lerp(r, 70, 20, 90, 0))


def score_drawdown(dd) -> float:
    """60日最大回撤(%)，dd<=0 → 分数。跌得越深分越高"""
    if dd is None or pd.isna(dd):
        return np.nan
    if dd <= -20:
        return 100.0
    if dd <= -10:
        return _lerp(dd, -20, 100, -10, 60)
    if dd <= -5:
        return _lerp(dd, -10, 60, -5, 40)
    return max(0.0, _lerp(dd, -5, 40, 0, 0))


def score_ma_dev(dev) -> float:
    """净值相对MA60偏离度(%) → 分数。负偏离（低于均线）高分"""
    if dev is None or pd.isna(dev):
        return np.nan
    if dev <= -15:
        return 100.0
    if dev <= 0:
        return _lerp(dev, -15, 100, 0, 50)
    if dev <= 10:
        return _lerp(dev, 0, 50, 10, 0)
    return 0.0


def score_pe_pct(pct) -> float:
    """估值历史百分位(0-100) → 分数。低估高分"""
    if pct is None or pd.isna(pct):
        return np.nan
    if pct <= 30:
        return _lerp(pct, 0, 100, 30, 70)
    if pct <= 70:
        return _lerp(pct, 30, 70, 70, 30)
    return max(0.0, _lerp(pct, 70, 30, 100, 0))


_DIM_FUNCS = {
    "premium": score_premium,
    "rsi": score_rsi,
    "drawdown": score_drawdown,
    "ma_dev": score_ma_dev,
    "pe": score_pe_pct,
}


def rating_of(score: float | None, premium: float | None = None) -> str:
    """评级。溢价一票否决：场内溢价 >= PREMIUM_VETO 时无论评分多少都是高危，
    因为高溢价买入当天先亏掉溢价，且溢价大概率回落。"""
    if premium is not None and not pd.isna(premium) and premium >= PREMIUM_VETO:
        return "🚫 溢价高危"
    if score is None or pd.isna(score):
        return "⚪ 数据不足"
    if score >= BUY_THRESHOLD:
        return "🟢 买入区"
    if score >= WATCH_THRESHOLD:
        return "🟡 观望/定投区"
    return "🔴 高估谨慎"


def compute_score(premium=None, rsi_v=None, dd=None, ma_dev=None,
                  pe_pct=None, macd_bonus: float = 0.0):
    """标量版：返回 (综合评分, 各维度分数字典)。无任何维度时返回 (None, {})"""
    raw = {
        "premium": score_premium(premium),
        "rsi": score_rsi(rsi_v),
        "drawdown": score_drawdown(dd),
        "ma_dev": score_ma_dev(ma_dev),
        "pe": score_pe_pct(pe_pct),
    }
    dims = {k: (None if (v is None or pd.isna(v)) else round(float(v), 1))
            for k, v in raw.items()}
    total_w = sum(WEIGHTS[k] for k, v in dims.items() if v is not None)
    if total_w <= 0:
        return None, dims
    score = sum(dims[k] * WEIGHTS[k] for k, v in dims.items() if v is not None) / total_w
    score = max(0.0, min(100.0, score + macd_bonus))
    return round(score, 1), dims


def score_series(df: pd.DataFrame, premium: pd.Series | None = None,
                 pe_pct: pd.Series | None = None) -> pd.DataFrame:
    """序列版：给 enriched df 增加 premium / pe_pct / 各维度得分 / score 列。
    premium、pe_pct 需与 df 行对齐（同 index），无数据传 None。"""
    out = df.copy()
    idx = df.index
    prem = premium if premium is not None else pd.Series(np.nan, index=idx)
    pep = pe_pct if pe_pct is not None else pd.Series(np.nan, index=idx)
    cols = {"premium": prem, "rsi": df["rsi"], "drawdown": df["dd60"],
            "ma_dev": df["dev60"], "pe": pep}
    out["premium"] = prem
    out["pe_pct"] = pep
    num = pd.Series(0.0, index=idx)
    den = pd.Series(0.0, index=idx)
    for k, func in _DIM_FUNCS.items():
        s = cols[k].map(func)
        out["s_" + k] = s
        num = num + s.fillna(0.0) * WEIGHTS[k]
        den = den + s.notna() * WEIGHTS[k]
    out["score"] = (num / den.where(den > 0)).clip(0, 100).round(1)
    return out
