"""
全局配置：基金池、信号权重与阈值、数据参数
改这里即可增删基金 / 调整评分规则
"""
from __future__ import annotations

import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "signal.db")
REPORT_PATH = os.path.join(BASE_DIR, "docs", "index.html")


@dataclass(frozen=True)
class FundConfig:
    code: str
    name: str
    market: str | None   # "sh" / "sz" / None 表示场外基金（无场内行情，跳过溢价率维度）
    index_name: str      # 跟踪指数：纳斯达克100 / 标普500


# 基金池（可自行增删）
FUNDS: list[FundConfig] = [
    FundConfig("513100", "纳指ETF(国泰)", "sh", "纳斯达克100"),
    FundConfig("159941", "纳指ETF(广发)", "sz", "纳斯达克100"),
    FundConfig("270042", "广发纳斯达克100联接A", None, "纳斯达克100"),
    FundConfig("161130", "易方达纳斯达克100LOF", "sz", "纳斯达克100"),
    FundConfig("513500", "标普500ETF(博时)", "sh", "标普500"),
    FundConfig("159655", "标普500ETF(华夏)", "sz", "标普500"),
    FundConfig("050025", "博时标普500ETF联接A", None, "标普500"),
    FundConfig("161125", "易方达标普500LOF", "sz", "标普500"),
]

# 信号维度权重（某维度无数据时自动按剩余维度归一化）
WEIGHTS = {
    "premium": 30.0,   # 溢价率（QDII 第一信号）
    "rsi": 25.0,       # RSI 超卖
    "drawdown": 20.0,  # 阶段最大回撤
    "ma_dev": 15.0,    # 均线偏离度
    "pe": 10.0,        # 估值分位（仅标普500，数据源 multpl）
}

# 评级阈值
BUY_THRESHOLD = 70.0     # >= 70 🟢 买入区
WATCH_THRESHOLD = 45.0   # 45~70 🟡 观望/定投区，< 45 🔴 高估谨慎

# 技术指标参数
RSI_PERIOD = 14
DRAWDOWN_WINDOW = 60
MA_SHORT, MA_LONG = 60, 250

# 溢价率提示
PREMIUM_WARN = 3.0       # 溢价 > 3% 提示"买入贵"
PREMIUM_CHEAP = 1.0      # 溢价 < 1% 认为便宜

# 数据抓取参数
NAV_PAGE_SIZE = 200      # 蛋卷净值每页条数
NAV_MAX_PAGES = 5        # 最多抓 5 页 ≈ 1000 个交易日 ≈ 4 年
PE_MAX_AGE_HOURS = 24    # multpl PE 缓存刷新间隔

# 回测持有期（交易日）
BACKTEST_HORIZONS = (5, 20, 60)
