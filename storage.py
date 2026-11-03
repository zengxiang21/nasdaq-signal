"""SQLite 存储层：净值 / K线 / 信号快照 / 估值缓存"""
from __future__ import annotations

import json
import os
import sqlite3

import pandas as pd

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nav_history (
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    nav  REAL,
    pct  REAL,
    PRIMARY KEY (code, date)
);
CREATE TABLE IF NOT EXISTS kline (
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, close REAL, high REAL, low REAL,
    volume REAL, amount REAL,
    PRIMARY KEY (code, date)
);
CREATE TABLE IF NOT EXISTS signals (
    code  TEXT NOT NULL,
    date  TEXT NOT NULL,
    score REAL,
    rating TEXT,
    details TEXT,
    PRIMARY KEY (code, date)
);
CREATE TABLE IF NOT EXISTS pe_history (
    date TEXT PRIMARY KEY,
    pe   REAL
);
CREATE TABLE IF NOT EXISTS fund_limits (
    code          TEXT NOT NULL,
    date          TEXT NOT NULL,
    status_buy    TEXT,
    status_redeem TEXT,
    daily_limit   REAL,
    min_buy       REAL,
    subscribe_rate REAL,
    dj_status     TEXT,
    can_buy       INTEGER,
    raw           TEXT,
    PRIMARY KEY (code, date)
);
CREATE TABLE IF NOT EXISTS kv_cache (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT
);
"""


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


# ---------- 净值 ----------
def upsert_nav(conn: sqlite3.Connection, code: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    pct = df["pct"] if "pct" in df.columns else pd.Series([None] * len(df), index=df.index)
    rows = [
        (code, d.strftime("%Y-%m-%d"),
         None if pd.isna(n) else float(n),
         None if pd.isna(p) else float(p))
        for d, n, p in zip(df["date"], df["nav"], pct)
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO nav_history (code, date, nav, pct) VALUES (?,?,?,?)", rows)
    conn.commit()
    return len(rows)


def load_nav(conn: sqlite3.Connection, code: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT date, nav, pct FROM nav_history WHERE code=? ORDER BY date",
        conn, params=(code,))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- K线 ----------
def upsert_kline(conn: sqlite3.Connection, code: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    rows = [(code, d.strftime("%Y-%m-%d"),
             *(None if pd.isna(v) else float(v) for v in (o, c, h, l, v, a)))
            for d, o, c, h, l, v, a in zip(
                df["date"], df["open"], df["close"], df["high"],
                df["low"], df["volume"], df["amount"])]
    conn.executemany(
        "INSERT OR REPLACE INTO kline (code, date, open, close, high, low, volume, amount)"
        " VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return len(rows)


def load_kline(conn: sqlite3.Connection, code: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT date, open, close, high, low, volume, amount FROM kline"
        " WHERE code=? ORDER BY date", conn, params=(code,))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- 信号快照 ----------
def upsert_signal(conn: sqlite3.Connection, code: str, date: str,
                  score: float | None, rating: str, details: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO signals (code, date, score, rating, details)"
        " VALUES (?,?,?,?,?)",
        (code, date, None if score is None else float(score), rating,
         json.dumps(details, ensure_ascii=False, default=str)))
    conn.commit()


def load_latest_signal(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute(
        "SELECT date, score, rating, details FROM signals"
        " WHERE code=? ORDER BY date DESC LIMIT 1", (code,)).fetchone()
    if not row:
        return None
    date, score, rating, details = row
    return {"date": date, "score": score, "rating": rating,
            "details": json.loads(details) if details else {}}


def latest_signal_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(date) FROM signals").fetchone()
    return row[0] if row else None


# ---------- 估值 ----------
def upsert_pe(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    rows = [(d.strftime("%Y-%m-%d"), None if pd.isna(v) else float(v))
            for d, v in zip(df["date"], df["pe"])]
    conn.executemany("INSERT OR REPLACE INTO pe_history (date, pe) VALUES (?,?)", rows)
    conn.commit()
    return len(rows)


def load_pe(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT date, pe FROM pe_history ORDER BY date", conn)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- 场外限额快照 ----------
def upsert_fund_limits(conn: sqlite3.Connection, code: str, date: str,
                       info: dict) -> None:
    """保存某日限额快照（info: status_buy/status_redeem/daily_limit/min_buy/
    subscribe_rate/dj_status/can_buy）"""
    conn.execute(
        "INSERT OR REPLACE INTO fund_limits"
        " (code, date, status_buy, status_redeem, daily_limit, min_buy,"
        "  subscribe_rate, dj_status, can_buy, raw) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (code, date,
         info.get("status_buy"), info.get("status_redeem"),
         info.get("daily_limit"), info.get("min_buy"), info.get("subscribe_rate"),
         info.get("dj_status"),
         None if info.get("can_buy") is None else int(bool(info.get("can_buy"))),
         json.dumps(info, ensure_ascii=False, default=str)))
    conn.commit()


def load_fund_limits(conn: sqlite3.Connection, code: str) -> list[dict]:
    """某基金全部历史限额快照（按日期升序），用于 diff 出限额风向事件"""
    rows = conn.execute(
        "SELECT date, status_buy, status_redeem, daily_limit, min_buy,"
        " subscribe_rate, dj_status, can_buy FROM fund_limits"
        " WHERE code=? ORDER BY date", (code,)).fetchall()
    keys = ("date", "status_buy", "status_redeem", "daily_limit", "min_buy",
            "subscribe_rate", "dj_status", "can_buy")
    return [dict(zip(keys, r)) for r in rows]


def load_latest_fund_limits(conn: sqlite3.Connection, code: str) -> dict | None:
    rows = load_fund_limits(conn, code)
    return rows[-1] if rows else None


# ---------- KV 缓存 ----------
def get_cache(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM kv_cache WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_cache(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO kv_cache (key, value, updated_at)"
        " VALUES (?,?, datetime('now', 'localtime'))", (key, value))
    conn.commit()
