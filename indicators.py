"""技术指标（纯 pandas 实现，避免 TA-Lib 在 Windows 的编译问题）"""
from __future__ import annotations

import pandas as pd

from config import DRAWDOWN_WINDOW, MA_LONG, MA_SHORT, RSI_PERIOD


def rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder RSI"""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    dif = (series.ewm(span=fast, adjust=False).mean()
           - series.ewm(span=slow, adjust=False).mean())
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2  # 国内软件柱状图惯例 ×2
    return dif, dea, hist


def enrich(nav_df: pd.DataFrame) -> pd.DataFrame:
    """给净值序列叠加指标列：rsi / dif / dea / hist / ma60 / ma250 / dev / dd"""
    df = nav_df.copy()
    s = df["nav"]
    df["rsi"] = rsi(s)
    dif, dea, hist = macd(s)
    df["dif"], df["dea"], df["hist"] = dif, dea, hist
    df["ma60"] = s.rolling(MA_SHORT, min_periods=MA_SHORT).mean()
    df["ma250"] = s.rolling(MA_LONG, min_periods=MA_LONG).mean()
    df["dev60"] = (s - df["ma60"]) / df["ma60"] * 100
    df["dev250"] = (s - df["ma250"]) / df["ma250"] * 100
    roll_max = s.rolling(DRAWDOWN_WINDOW, min_periods=1).max()
    df["dd60"] = (s - roll_max) / roll_max * 100
    return df
