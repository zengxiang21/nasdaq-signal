"""推送提醒：Server酱(微信) / Telegram / Bark
通过环境变量配置，未配置的渠道自动跳过：
  SERVERCHAN_SENDKEY  - Server酱 SendKey（微信推送）
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
  BARK_URL            - 如 https://api.day.app/你的key

消息内容读 scripts/export_web_data.py 生成的 summary.json / limits.json
（先跑导出再推送，口径与网站完全一致）。
"""
from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path

import requests

from config import WEB_DATA_DIR


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def send_serverchan(title: str, content: str) -> bool:
    key = _env("SERVERCHAN_SENDKEY")
    if not key:
        return False
    try:
        requests.post(f"https://sctapi.ftqq.com/{key}.send",
                      data={"title": title, "desp": content}, timeout=10)
        return True
    except Exception:  # noqa: BLE001
        return False


def send_telegram(text: str) -> bool:
    token, chat = _env("TELEGRAM_BOT_TOKEN"), _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text}, timeout=10)
        return True
    except Exception:  # noqa: BLE001
        return False


def send_bark(title: str, body: str) -> bool:
    base = _env("BARK_URL").rstrip("/")
    if not base:
        return False
    try:
        requests.get(f"{base}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}",
                     timeout=10)
        return True
    except Exception:  # noqa: BLE001
        return False


def build_message() -> tuple[str, bool]:
    """返回 (消息文本, 是否有值得关注的信号)"""
    web = Path(WEB_DATA_DIR)
    try:
        summary = json.loads((web / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", False
    lines: list[str] = []
    interesting = False

    # 温度计
    t = summary.get("temperature") or {}
    if t.get("temp") is not None:
        lines.append(f"🌡 QDII 贪婪温度 {t['temp']:.0f}°（{t.get('level')}）"
                     f"｜溢价中位 {t.get('premium_median'):+.2f}%"
                     f"｜限购拥挤 {t.get('crowd_ratio'):.0f}%")
        if t["temp"] >= 70:
            interesting = True

    # 每指数决策一句话
    funds = summary.get("funds") or {}
    for idx_name in ("纳斯达克100", "标普500"):
        market = [(c, f) for c, f in funds.items()
                  if f.get("index_name") == idx_name and f.get("market") and f.get("card")]
        otc = [(c, f) for c, f in funds.items()
               if f.get("index_name") == idx_name and not f.get("market") and f.get("card")]
        if not market:
            continue
        best = min(market, key=lambda kv: (kv[1]["card"].get("premium_now")
                                           if kv[1]["card"].get("premium_now") is not None else 999))
        prem = best[1]["card"].get("premium_now")
        prem_s = f"{prem:+.2f}%" if prem is not None else "-"
        buyable = [(c, f) for c, f in otc
                   if f.get("limits") and f["limits"].get("daily_limit")
                   and "暂停" not in (f["limits"].get("status_buy") or "")]
        otc_best = max(buyable, key=lambda kv: kv[1]["limits"]["daily_limit"]) if buyable else None
        otc_s = (f"场外可走 {otc_best[1]['name']} 限额 {otc_best[1]['limits']['daily_limit']:.0f}元/日"
                 if otc_best else "场外全部暂停/限购")
        lines.append(f"\n【{idx_name}】最优场内溢价 {prem_s}（{best[1]['name']} {best[0]}，"
                     f"{best[1]['card']['rating']} 评分 {best[1]['card']['score']}）\n{otc_s}")
        if prem is not None and prem >= 10:
            interesting = True

    # 限额风向
    try:
        limits = json.loads((web / "limits.json").read_text(encoding="utf-8"))
        for e in (limits.get("events") or [])[:5]:
            lines.append(f"\n🔁 {e['date']} {e['name']} {e['field']}: {e['from']} → {e['to']}")
            interesting = True
    except (OSError, json.JSONDecodeError):
        pass

    return "\n".join(lines), interesting


def send_alerts(force: bool = False) -> bool:
    msg, interesting = build_message()
    if not msg:
        return False
    if not interesting and not force:
        return False
    title = "纳指/标普500 买入信号"
    return any([send_serverchan(title, msg),
                send_telegram(msg),
                send_bark(title, msg)])
