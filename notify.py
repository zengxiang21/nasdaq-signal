"""推送提醒：Server酱(微信) / Telegram / Bark
通过环境变量配置，未配置的渠道自动跳过：
  SERVERCHAN_SENDKEY  - Server酱 SendKey（微信推送）
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
  BARK_URL            - 如 https://api.day.app/你的key
"""
from __future__ import annotations

import os
import urllib.parse

import requests

import storage
from config import BUY_THRESHOLD, FUNDS, PREMIUM_WARN


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
    conn = storage.get_conn()
    lines, interesting = [], False
    for f in FUNDS:
        sig = storage.load_latest_signal(conn, f.code)
        if not sig or sig["score"] is None:
            continue
        d = sig["details"]
        prem = d.get("premium_now")
        if prem is None:
            prem = d.get("premium_close")
        prem_s = f"{prem:+.2f}%" if prem is not None else "场外"
        rsi_s = f"{d['rsi']:.1f}" if d.get("rsi") is not None else "-"
        if sig["score"] >= BUY_THRESHOLD or (prem is not None and prem >= PREMIUM_WARN):
            interesting = True
        lines.append(f"{sig['rating']} {f.name}\n"
                     f"评分 {sig['score']:.1f} | 溢价 {prem_s} | RSI {rsi_s} | 净值 {d.get('nav')}")
    conn.close()
    return "\n\n".join(lines), interesting


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
