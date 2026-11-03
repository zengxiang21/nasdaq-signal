"""CLI 入口：每日更新数据 / 生成静态报告 / 推送
用法：
  python update.py                 # 只更新数据与信号快照
  python update.py --report        # 同时生成 docs/index.html（GitHub Pages 用）
  python update.py --notify        # 同时推送（Server酱/Telegram/Bark，环境变量配置）
"""
from __future__ import annotations

import argparse
import sys

# Windows 控制台默认 GBK，打印 emoji 评级会崩溃，强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pipeline
import report
from notify import send_alerts


def main() -> None:
    p = argparse.ArgumentParser(description="纳指/标普500 买入信号每日更新")
    p.add_argument("--report", action="store_true", help="生成静态 HTML 报告")
    p.add_argument("--notify", action="store_true", help="发送推送提醒")
    args = p.parse_args()

    print("== 开始更新数据 ==")
    pipeline.update_all(verbose=True)
    if args.report:
        path = report.generate_report()
        print(f"== 静态报告已生成: {path} ==")
    if args.notify:
        ok = send_alerts()
        print(f"== 推送{'已发送' if ok else '未触发（无买入区信号或未配置渠道）'} ==")


if __name__ == "__main__":
    main()
