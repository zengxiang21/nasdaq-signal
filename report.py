"""生成静态 HTML 报告（docs/index.html，可配合 GitHub Pages 访问）"""
from __future__ import annotations

import os
from datetime import datetime

import storage
from config import FUNDS, REPORT_PATH


def generate_report(path: str = REPORT_PATH) -> str:
    conn = storage.get_conn()
    rows = []
    for f in FUNDS:
        sig = storage.load_latest_signal(conn, f.code)
        if not sig or sig["score"] is None:
            rows.append((f.name, f.code, "-", "⚪ 数据不足", "-", "-", "场外", "-"))
            continue
        d = sig["details"]
        prem = d.get("premium_now")
        if prem is None:
            prem = d.get("premium_close")
        prem_s = f"{prem:+.2f}%" if prem is not None else "场外申购"
        rsi_s = f"{d['rsi']:.1f}" if d.get("rsi") is not None else "-"
        rows.append((f.name, f.code, f"{sig['score']:.1f}", sig["rating"],
                     f"{d.get('nav')}", d.get("nav_date"), prem_s, rsi_s))
    conn.close()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = "\n".join(
        f"<tr><td>{r[0]}</td><td class='code'>{r[1]}</td><td><b>{r[2]}</b></td>"
        f"<td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td><td>{r[7]}</td></tr>"
        for r in rows)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>纳指/标普500 买入信号</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 980px; margin: 24px auto; padding: 0 16px; color: #1f2328; }}
  h1 {{ font-size: 22px; }}
  .time {{ color: #6e7781; font-size: 13px; margin-bottom: 16px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  th, td {{ border: 1px solid #d1d9e0; padding: 8px 10px; text-align: left; }}
  th {{ background: #f6f8fa; }}
  .code {{ color: #6e7781; font-family: monospace; }}
  .foot {{ margin-top: 20px; font-size: 12px; color: #6e7781; line-height: 1.7; }}
</style>
</head>
<body>
<h1>📈 纳指 / 标普500 买入时机信号</h1>
<div class="time">生成时间：{now}（数据源：蛋卷基金 / 东方财富 / multpl）</div>
<table>
<tr><th>基金</th><th>代码</th><th>综合评分</th><th>评级</th><th>最新净值</th>
    <th>净值日期</th><th>场内溢价率</th><th>RSI(14)</th></tr>
{body}
</table>
<div class="foot">
  <p><b>评分规则</b>：溢价率(30%) + RSI(25%) + 60日回撤(20%) + 均线偏离(15%) + 估值分位(10%)，
  加权合成 0-100 分；≥70 🟢买入区，45-70 🟡观望/定投区，&lt;45 🔴高估谨慎。
  场外基金无溢价率维度，权重自动归一化。</p>
  <p><b>免责声明</b>：本页面仅为技术指标统计，不构成任何投资建议。投资有风险，操作需谨慎。</p>
</div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path
