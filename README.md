# 📈 纳指 / 标普500 买入信号

每日回答三个问题：**哪里还买得进？现在买贵不贵？历史上这时候买入胜率多少？**

对标微信小程序「纳纳小助手」的开源实现。区别只有一个：**所有数字怎么算出来的，全部公开在「说明」页**——评分公式、溢价口径、温度计公式、回测口径，无一黑箱。

## 功能

| 页面 | 内容 |
|---|---|
| **今日** | QDII 贪婪温度计（溢价中位数 × 限购拥挤度）+ 纳指/标普决策卡（最优场内溢价、场外还能买哪只、一句话建议）+ 23 只基金评分总表 |
| **场内溢价** | 12 只 ETF/LOF 实时溢价（浏览器直连腾讯行情）+ 30/90/365 日溢价分位 + 单只溢价历史图；溢价 ≥10% 一票否决标 🚫 |
| **场外限额** | 11 只 QDII 申购状态/日限额/费率（天天基金 F10 口径）+ 每日快照自动 diff 出的「限额风向」事件流 |
| **长历史** | 标普500（1986-）/ 纳指综合（1991-）逐年收益与年内最大回撤、纳指 vs 标普复利对比、连跌统计 |
| **胜率回测** | 指数+场内基金全标的，规则（星期几/连跌N天/单日大跌/均线偏离/RSI/回撤/溢价）× 持有期（1~60日）——**在浏览器里实时调参计算**，样本 <30 灰显防误导 |
| **工具** | A/C 类持有成本计算器（含盈亏平衡天数）+ 定投日选择回测 |
| **说明** | 全口径文档 + 免责声明 |

评分引擎：溢价 30% + RSI 25% + 60日回撤 20% + 均线偏离 15% + 估值分位 10%，场内溢价 ≥10% 一票否决。

## 架构

```
├── Python 数据层（复用/扩展自早期版本）
│   ├── config.py              # 基金池（23只）、权重、指数 secid
│   ├── fetchers.py            # 蛋卷净值/详情 · 东财K线/行情 · 天天基金F10限额 · multpl PE · 腾讯行情
│   ├── storage.py             # SQLite：净值/K线/信号/限额快照
│   ├── signals.py             # 评分引擎（溢价一票否决）
│   ├── backtest.py            # 回测引擎（与前端 TS 同口径）
│   ├── pipeline.py / notify.py / update.py
│   └── scripts/export_web_data.py   # 生成 web/public/data/*.json（前端唯一数据源）
└── web/                       # React 19 + Vite 6 + TS + Tailwind 4 + Recharts
    └── src/{lib,pages}        # 数据加载 · 腾讯实时直连 · 回测TS引擎 · 7个页面
```

**数据流**：GitHub Actions 每晚北京时间 20:00/21:00 抓数 → 生成 JSON 提交回仓库 → Pages 工作流构建静态站。抓取失败时仓库里永远有昨天的数据兜底；页面打开时再由浏览器直连腾讯行情把场内溢价升级为实时。

## 快速开始（本地）

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
run.bat        # 更新数据 + 构建前端 + 本机服务 http://localhost:8511/
```

只想重建站点不更新数据：`python scripts/export_web_data.py` 后 `cd web && npm run dev`。

## GitHub 部署（全自动）

1. 推送本仓库到 GitHub（main 分支）
2. Settings → Pages → Source 选 **GitHub Actions**
3. 可选推送：Settings → Secrets 添加 `SERVERCHAN_SENDKEY`（或 `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` / `BARK_URL`）
4. 两个工作流自动运行：
   - `data-daily.yml`：每晚 20:00/21:00（北京时间）抓数、导出 JSON、提交回仓库、触发推送
   - `deploy-pages.yml`：push 后构建发布 Pages，站点地址 `https://<用户名>.github.io/nasdaq-signal/`

本地计划任务同理：每天 20:30 执行 `python scripts/export_web_data.py --update`。

## 数据源

| 数据 | 来源 |
|---|---|
| 场外限额/费率 | 天天基金 F10（每日快照存档 + 自动 diff） |
| 场外净值/申赎状态 | 蛋卷基金 djapi |
| 场内行情/日K、指数长历史 | 东方财富 push2his（标普500 自 1986、纳指综合自 1991） |
| 标普500 PE | multpl.com（Shiller 月度） |
| 实时行情 | 腾讯 qt.gtimg.cn（浏览器直连，CORS 开放） |

## 项目沿革

- v1：Streamlit 仪表盘（`app.py`，`python -m streamlit run app.py` 仍可用）——快速验证数据链路
- v2（当前）：React 静态站 + Actions 全自动数据管线，对标纳纳小助手全功能

## 免责声明

本项目仅为技术指标统计工具，**不构成任何投资建议**。历史胜率不代表未来表现，限额/费率以基金公司与销售渠道为准。投资有风险，操作需谨慎。
