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
WEB_DATA_DIR = os.path.join(BASE_DIR, "web", "public", "data")


@dataclass(frozen=True)
class FundConfig:
    code: str
    name: str
    kind: str           # "etf"(场内ETF) / "lof"(场内LOF) / "otc"(场外申赎)
    market: str | None  # "sh" / "sz" / None(场外)
    index_name: str     # 纳斯达克100 / 标普500
    share: str = ""     # 份额类别 A / C / 人民币A / 美元汇A ...

    @property
    def on_market(self) -> bool:
        return self.market is not None


# 基金池（代码已通过 FundSearchAPI / 东财 K 线核实，可自行增删）
FUNDS: list[FundConfig] = [
    # ---- 场内 ETF：纳斯达克100 ----
    FundConfig("513100", "纳指ETF(国泰)", "etf", "sh", "纳斯达克100"),
    FundConfig("159941", "纳指ETF(广发)", "etf", "sz", "纳斯达克100"),
    FundConfig("513300", "纳指ETF(华夏)", "etf", "sh", "纳斯达克100"),
    FundConfig("159632", "纳指ETF(华安)", "etf", "sz", "纳斯达克100"),
    FundConfig("159659", "纳指ETF(招商)", "etf", "sz", "纳斯达克100"),
    FundConfig("159513", "纳指ETF(大成)", "etf", "sz", "纳斯达克100"),
    # ---- 场内 ETF：标普500 ----
    FundConfig("513500", "标普500ETF(博时)", "etf", "sh", "标普500"),
    FundConfig("513650", "标普500ETF(南方)", "etf", "sh", "标普500"),
    FundConfig("159612", "标普500ETF(国泰)", "etf", "sz", "标普500"),
    FundConfig("159655", "标普500ETF(华夏)", "etf", "sz", "标普500"),
    # ---- 场内 LOF ----
    FundConfig("161130", "易方达纳斯达克100LOF", "lof", "sz", "纳斯达克100"),
    FundConfig("161125", "易方达标普500LOF", "lof", "sz", "标普500"),
    # ---- 场外 LOF/指数（无场内行情，按场外口径监控） ----
    FundConfig("160213", "国泰纳斯达克100指数", "otc", None, "纳斯达克100"),
    # ---- 场外：纳斯达克100 ----
    FundConfig("270042", "广发纳指联接A", "otc", None, "纳斯达克100", "A"),
    FundConfig("006479", "广发纳指联接C", "otc", None, "纳斯达克100", "C"),
    FundConfig("000834", "大成纳指联接A", "otc", None, "纳斯达克100", "A"),
    FundConfig("016452", "南方纳指发起A", "otc", None, "纳斯达克100", "A"),
    FundConfig("016453", "南方纳指发起C", "otc", None, "纳斯达克100", "C"),
    FundConfig("018043", "天弘纳指发起A", "otc", None, "纳斯达克100", "A"),
    FundConfig("018044", "天弘纳指发起C", "otc", None, "纳斯达克100", "C"),
    # ---- 场外：标普500 ----
    FundConfig("050025", "博时标普联接A", "otc", None, "标普500", "A"),
    FundConfig("006075", "博时标普联接C", "otc", None, "标普500", "C"),
    FundConfig("012860", "易方达标普人民币C", "otc", None, "标普500", "C"),
]

# 长历史指数（东财 secid → 展示名）
INDEXES: dict[str, dict] = {
    "spx": {"secid": "100.SPX", "name": "标普500", "since": 1986},
    "ndx": {"secid": "100.NDX", "name": "纳斯达克综合", "since": 1991,
            "note": "纳指100 本体东财仅 2019 年起有数据，长历史统计用纳指综合（走势高度同步），2019 年后可对照 NDX100"},
    "ndx100": {"secid": "100.NDX100", "name": "纳斯达克100", "since": 2019},
}

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

# 溢价一票否决：场内溢价超过该值时，无论评分多少都标红"勿追"
PREMIUM_VETO = 10.0
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
BACKTEST_HORIZONS = (1, 3, 5, 10, 20, 60)

# 情绪温度计：温度 = 0.6×溢价中位数分 + 0.4×限购拥挤度分
TEMP_PREMIUM_WEIGHT = 0.6
TEMP_CROWD_WEIGHT = 0.4
