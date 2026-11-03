# 📈 纳指 / 标普500 买入时机信号工具

每日自动回答一个问题：**现在买纳斯达克 / 标普500，划算吗？**

替代「纳纳小助手」等微信小程序的开源方案，支持本地部署和 GitHub 自动部署。

## 功能

- **综合评分（0-100）**：溢价率(30%) + RSI(25%) + 60日回撤(20%) + 均线偏离(15%) + 估值分位(10%)
- **评级建议**：≥70 🟢 买入区（适合一把梭/加仓）｜45-70 🟡 观望/定投区｜<45 🔴 高估谨慎
- **场内溢价率**：QDII 第一信号，溢价 >3% 提示买入贵（实时行情计算）
- **净值走势图**：净值 + MA60/MA250 + 买入信号标记 + 溢价率历史
- **历史胜率回测**：各信号规则触发后 5/20/60 日的盈利概率，与基准对照
- **每日自动更新 + 推送**：GitHub Actions / 本地计划任务，支持 Server酱(微信)/Telegram/Bark

## 快速开始（本地）

```bash
cd nasdaq-signal
pip install -r requirements.txt
run.bat                # 或: python -m streamlit run app.py
```

浏览器打开 http://localhost:8501 。首次打开会自动抓取数据（约 30 秒）。

## 每日更新（本地）

```bash
python update.py                 # 更新数据与信号
python update.py --report        # 同时生成 docs/index.html 静态报告
python update.py --notify        # 同时推送
```

可用 Windows 任务计划程序设置每天 20:30 执行 `python update.py --notify`。

## GitHub 部署（全自动）

1. 推送本仓库到 GitHub
2. Settings → Pages → Source 选 `Deploy from a branch` → 分支 `main` / `docs` 目录（静态报告）
3. 如需推送：Settings → Secrets 添加 `SERVERCHAN_SENDKEY`（或 `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` / `BARK_URL`）
4. `.github/workflows/daily.yml` 已配置每天 20:00 / 22:00（北京时间）自动运行，更新数据并提交回仓库

## 配置

所有可调项在 `config.py`：

- `FUNDS`：基金池（code, 名称, 市场 sh/sz/None, 跟踪指数），可自由增删
- `WEIGHTS`：五个维度的权重
- `BUY_THRESHOLD` / `WATCH_THRESHOLD`：评级阈值
- `PREMIUM_WARN` / `PREMIUM_CHEAP`：溢价率提示线

## 数据源

| 数据 | 来源 |
|---|---|
| 基金净值历史 | 蛋卷基金 danjuanfunds.com |
| 场内实时行情/日K | 东方财富 push2 / push2his |
| 标普500 PE 历史 | multpl.com（Shiller 数据） |

## 项目结构

```
├── config.py       # 基金池、权重、阈值
├── fetchers.py     # 数据抓取
├── storage.py      # SQLite 存储
├── indicators.py   # RSI/MACD/均线/回撤
├── signals.py      # 评分引擎
├── backtest.py     # 胜率回测
├── pipeline.py     # 更新编排
├── notify.py       # 推送
├── report.py       # 静态 HTML 报告
├── app.py          # Streamlit 仪表盘
├── update.py       # CLI 入口
└── data/signal.db  # SQLite 数据库（自动生成）
```

## 免责声明

本项目仅为技术指标统计工具，**不构成任何投资建议**。历史胜率不代表未来表现，投资有风险，操作需谨慎。
