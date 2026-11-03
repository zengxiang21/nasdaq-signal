"""Streamlit 仪表盘入口：python -m streamlit run app.py"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import pipeline
import storage
from backtest import backtest_to_df
from config import BUY_THRESHOLD, FUNDS, PREMIUM_WARN, WATCH_THRESHOLD

st.set_page_config(page_title="纳指/标普500 买入信号", page_icon="📈", layout="wide")

C_BUY, C_WATCH, C_SELL = "#2da44e", "#bf8700", "#cf222e"


@st.cache_data(ttl=300)
def get_snapshots() -> dict:
    conn = storage.get_conn()
    out = {f.code: storage.load_latest_signal(conn, f.code) for f in FUNDS}
    conn.close()
    return out


@st.cache_data(ttl=600)
def get_analysis(code: str):
    conn = storage.get_conn()
    pe_df = pipeline.get_pe_df(conn)
    fund = next((f for f in FUNDS if f.code == code), None)
    if fund is None:
        conn.close()
        return None
    res = pipeline.analyze_fund(conn, fund, pe_df)
    conn.close()
    return res


def rating_color(rating: str) -> str:
    if rating.startswith("🟢"):
        return C_BUY
    if rating.startswith("🟡"):
        return C_WATCH
    if rating.startswith("🔴"):
        return C_SELL
    return "#6e7781"


def badge(text: str, color: str) -> None:
    st.markdown(
        f"<span style='background:{color};color:#fff;padding:3px 12px;"
        f"border-radius:12px;font-weight:600;font-size:14px'>{text}</span>",
        unsafe_allow_html=True)


def action_advice(score, premium) -> str:
    if score is None:
        return "数据不足，请点击左侧「立即更新数据」。"
    if score >= BUY_THRESHOLD:
        base = "处于买入区，适合买入/加仓（含一把梭抄底）。"
        if premium is not None and premium >= PREMIUM_WARN:
            base += f" 但场内溢价 {premium:.2f}% 偏高，建议优先场外申购或等溢价回落再买。"
        return base
    if score >= WATCH_THRESHOLD:
        return "观望/定投区：适合定投分批建仓，不适合重仓一把梭。"
    return "高估谨慎：建议等待回调或减少买入金额。"


# ---------- 启动时自动更新（当天无信号才联网） ----------
if "booted" not in st.session_state:
    try:
        pipeline.refresh_if_stale(max_age_hours=20)
    except Exception as e:  # noqa: BLE001
        st.warning(f"自动更新失败：{e}")
    st.session_state["booted"] = True
    st.cache_data.clear()

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("操作")
    if st.button("🔄 立即更新数据", width="stretch"):
        with st.spinner("正在抓取数据并计算信号，约需 30 秒…"):
            try:
                pipeline.update_all()
            except Exception as e:  # noqa: BLE001
                st.error(f"更新失败：{e}")
        st.cache_data.clear()
        st.rerun()
    if st.button("📤 测试推送", width="stretch"):
        import notify
        ok = notify.send_alerts(force=True)
        if ok:
            st.success("已发送，请检查你配置的渠道")
        else:
            st.warning("未配置任何推送渠道，详见 README（Server酱/Telegram/Bark）")
    st.divider()
    st.caption("数据源：蛋卷基金 / 东方财富 / multpl")
    st.caption("QDII 净值一般晚间披露，建议 20:00 后查看最新信号")


def render_overview() -> None:
    st.subheader("今日信号总览")
    st.caption("≥70 🟢 买入区 ｜ 45-70 🟡 观望/定投区 ｜ <45 🔴 高估谨慎")
    snaps = get_snapshots()
    dim_names = {"premium": "溢价率", "rsi": "RSI", "drawdown": "60日回撤",
                 "ma_dev": "均线偏离", "pe": "估值分位"}
    for f in FUNDS:
        st.markdown("---")
        sig = snaps.get(f.code)
        if not sig or sig["score"] is None:
            st.markdown(f"**{f.name}** `{f.code}`")
            st.warning("暂无数据，请点击左侧「立即更新数据」")
            continue
        d = sig["details"]
        prem = d.get("premium_now")
        if prem is None:
            prem = d.get("premium_close")
        c1, c2, c3, c4, c5, c6 = st.columns([1.4, 1, 1.3, 1.1, 1, 1])
        with c1:
            st.markdown(f"**{f.name}**  \n`{f.code}` · {f.index_name}")
            badge(sig["rating"], rating_color(sig["rating"]))
        with c2:
            st.metric("综合评分", f"{sig['score']:.1f}")
        with c3:
            pct = d.get("pct")
            st.metric("最新净值", f"{d.get('nav')}",
                      f"{pct:+.2f}%" if pct is not None else None)
            st.caption(f"净值日期 {d.get('nav_date')}")
        with c4:
            st.metric("场内溢价率", f"{prem:+.2f}%" if prem is not None else "场外")
        with c5:
            rsi = d.get("rsi")
            st.metric("RSI(14)", f"{rsi:.1f}" if rsi is not None else "-")
        with c6:
            dd = d.get("dd60")
            st.metric("60日回撤", f"{dd:.1f}%" if dd is not None else "-")
        with st.expander("信号明细与操作建议"):
            st.markdown(f"**操作建议**：{action_advice(sig['score'], prem)}")
            dims = d.get("dims") or {}
            rows = [{"维度": dim_names[k],
                     "得分": f"{v:.0f}" if v is not None else "无数据"}
                    for k, v in dims.items()]
            st.table(pd.DataFrame(rows))
            notes = []
            if d.get("macd_bonus"):
                notes.append("MACD 近期" + ("金叉 +5" if d["macd_bonus"] > 0 else "死叉 -5"))
            if d.get("pe_pct") is not None:
                notes.append(f"标普500 PE 历史百分位 {d['pe_pct']:.1f}%")
            if prem is not None and prem >= PREMIUM_WARN:
                notes.append(f"⚠️ 溢价 {prem:.2f}% 超过 {PREMIUM_WARN:.0f}% 警戒线，买入成本偏高")
            for n in notes:
                st.caption(n)


def render_chart_tab() -> None:
    st.subheader("净值走势与买入信号标记")
    options = [f"{f.name} ({f.code})" for f in FUNDS]
    label = st.selectbox("选择基金", options, key="chart_fund")
    fund = next(f for f in FUNDS if f"{f.name} ({f.code})" == label)
    res = get_analysis(fund.code)
    if res is None:
        st.warning("数据不足，请先更新数据")
        return
    scored = res["scored"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=scored["date"], y=scored["nav"],
                             name="单位净值", line=dict(color="#0969da", width=2)))
    if scored["ma60"].notna().any():
        fig.add_trace(go.Scatter(x=scored["date"], y=scored["ma60"], name="MA60",
                                 line=dict(dash="dash", color="#bf8700")))
    if scored["ma250"].notna().any():
        fig.add_trace(go.Scatter(x=scored["date"], y=scored["ma250"], name="MA250",
                                 line=dict(dash="dash", color="#8250df")))
    buys = scored[scored["score"] >= BUY_THRESHOLD]
    if not buys.empty:
        fig.add_trace(go.Scatter(x=buys["date"], y=buys["nav"], mode="markers",
                                 name=f"评分≥{BUY_THRESHOLD:.0f}",
                                 marker=dict(color=C_BUY, size=10, symbol="triangle-up")))
    fig.update_layout(height=460, margin=dict(l=20, r=20, t=30, b=20),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, width="stretch")
    if fund.market and scored["premium"].notna().any():
        st.markdown("**场内溢价率历史**（溢价率 = 场内收盘价 / 基金净值 - 1）")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=scored["date"], y=scored["premium"],
                                  name="溢价率", fill="tozeroy",
                                  line=dict(color=C_SELL)))
        fig2.add_hline(y=PREMIUM_WARN, line_dash="dash",
                       annotation_text=f"{PREMIUM_WARN:.0f}% 警戒线")
        fig2.update_layout(height=240, margin=dict(l=20, r=20, t=30, b=20),
                           yaxis_title="溢价率 %")
        st.plotly_chart(fig2, width="stretch")


def render_backtest_tab() -> None:
    st.subheader("历史胜率回测")
    st.caption("在信号触发日买入，持有 N 个交易日后的盈利概率（基于基金历史净值，未计申购费）")
    options = [f"{f.name} ({f.code})" for f in FUNDS]
    label = st.selectbox("选择基金", options, key="bt_fund")
    fund = next(f for f in FUNDS if f"{f.name} ({f.code})" == label)
    res = get_analysis(fund.code)
    if res is None:
        st.warning("数据不足，请先更新数据")
        return
    df = backtest_to_df(res["backtest"])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("「基准：任意一天买入」用于对照——信号胜率应显著高于基准才有意义。")


def render_help_tab() -> None:
    st.subheader("评分方法与使用说明")
    st.markdown(f"""
**综合评分 = 五个维度加权（0-100，越高越适合买入）**

| 维度 | 权重 | 打分逻辑 |
|---|---|---|
| 溢价率 | 30% | ≤0% 折价得 100 分；1% 得 80；3% 得 50；≥10% 得 0（QDII 第一信号） |
| RSI(14) | 25% | ≤20 得 100；30 得 80；50 得 50；≥90 得 0 |
| 60日回撤 | 20% | ≥20% 回撤得 100；10% 得 60；无回撤得 0 |
| 均线偏离 | 15% | 低于 MA60 超 15% 得 100；持平得 50；高出 10% 得 0 |
| 估值分位 | 10% | 标普500 PE 历史百分位，低估高分（仅标普500基金，multpl 数据） |

- 某维度无数据时（如场外基金无溢价率），权重按剩余维度自动归一化
- MACD 近 3 日金叉 +5 分 / 死叉 -5 分
- **评级**：≥{BUY_THRESHOLD:.0f} 🟢 买入区｜{WATCH_THRESHOLD:.0f}-{BUY_THRESHOLD:.0f} 🟡 观望/定投区｜<{WATCH_THRESHOLD:.0f} 🔴 高估谨慎

**「一把梭」还是「定投」？**
- 🟢 买入区：适合一次性买入或加仓；若溢价率 >{PREMIUM_WARN:.0f}%，建议改走场外申购
- 🟡 观望区：适合定投分批
- 🔴 高估区：建议等待

**数据说明**
- 净值：蛋卷基金（每日晚间披露）；行情：东方财富；估值：multpl（Shiller 数据）
- QDII 净值 T+1 披露，盘中看到的信号基于最近已披露净值 + 实时场内价格

> ⚠️ 免责声明：本工具仅为技术指标统计工具，不构成任何投资建议。投资有风险，操作需谨慎。
""")


st.title("📈 纳指 / 标普500 买入时机信号")
st.caption("每日回答一个问题：现在买，划算吗？")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 信号总览", "📈 净值走势", "🎯 胜率回测", "📖 说明"])
with tab1:
    render_overview()
with tab2:
    render_chart_tab()
with tab3:
    render_backtest_tab()
with tab4:
    render_help_tab()
