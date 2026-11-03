import { Card, SectionTitle } from "../components/ui";

const DIMS: [string, string, string][] = [
  ["溢价率", "30%", "场内价 ÷ 最新净值 - 1。≤0 折价=100分，1%=80，3%=50，5%=20，10%+ = 0 分。QDII 的第一信号：高溢价买入先亏溢价"],
  ["RSI(14)", "25%", "Wilder RSI。≤20 = 100分，30 = 80，50 = 50，70 = 20，90+ = 0 分（超卖高分）"],
  ["60日回撤", "20%", "近 60 个交易日内峰谷最大跌幅。≤-20% = 100分，-10% = 60，-5% = 40，0 = 0 分"],
  ["均线偏离", "15%", "净值相对 MA60 偏离度。≤-15% = 100分，0 = 50，+10% 及以上 = 0 分"],
  ["估值分位", "10%", "标普500 PE 历史百分位（multpl 月度数据，仅标普系基金参与计分）。≤30% = 70-100分，70%+ 走低"],
];

export default function About() {
  return (
    <div className="space-y-6">
      <SectionTitle
        title="口径说明"
        sub="对标微信小程序「纳纳小助手」的开源实现——区别只有一个：这里所有数字怎么算出来的，全部写在下面"
      />

      <Card className="p-5">
        <h3 className="mb-2 font-semibold text-zinc-100">这个网站回答什么</h3>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-zinc-400">
          <li><b className="text-zinc-200">哪里还买得进</b>：场外 QDII 限额监控（2026 年额度紧张，大量基金单日限购 10~100 元甚至暂停）</li>
          <li><b className="text-zinc-200">现在买贵不贵</b>：场内 ETF 溢价 + 溢价历史分位，溢价过高时直接标红一票否决</li>
          <li><b className="text-zinc-200">长期是什么体验</b>：40 年逐年收益/回撤统计，稳定定投心态</li>
          <li><b className="text-zinc-200">信号历史上灵不灵</b>：胜率回测，样本量、盈亏比、基准对照全透明</li>
        </ul>
        <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs leading-relaxed text-amber-300/90">
          明确不做什么：不预测明天涨跌、不荐股、不承诺任何「胜率高的买点必然赚钱」。
          所有统计都基于历史，而历史的最大教训就是它不简单重复。
        </p>
      </Card>

      <Card className="p-5">
        <h3 className="mb-3 font-semibold text-zinc-100">综合评分（0-100）</h3>
        <div className="space-y-2">
          {DIMS.map(([name, w, desc]) => (
            <div key={name} className="flex gap-3 rounded-lg border border-zinc-800/70 bg-zinc-950/40 px-3 py-2">
              <span className="w-28 shrink-0 text-sm font-medium text-zinc-200">{name}</span>
              <span className="num w-10 shrink-0 text-sm text-sky-400">{w}</span>
              <span className="text-xs leading-relaxed text-zinc-500">{desc}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-zinc-500">
          某维度无数据时（如纳指系无 PE），按剩余维度权重归一化。评级：≥70 🟢 买入区 ｜ 45-70 🟡 观望/定投区 ｜ &lt;45 🔴 高估谨慎。
        </p>
        <div className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/5 px-3 py-2.5 text-sm">
          <b className="text-rose-400">溢价一票否决</b>
          <span className="ml-2 text-zinc-400">
            场内溢价 ≥10% 时，无论评分多少直接标 🚫 溢价高危——高溢价买入当天先亏溢价，且 QDII 高溢价最终大概率以溢价回落收场（2026 年多只 ETF 溢价超 15% 后回落）。
          </span>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="mb-2 font-semibold text-zinc-100">QDII 贪婪温度计</h3>
        <p className="text-sm leading-relaxed text-zinc-400">
          温度 = 100 −（0.6 × 场内溢价便宜分 + 0.4 × 限购宽松分）。
          溢价便宜分 = 场内基金溢价<b className="text-zinc-200">中位数</b>代入评分曲线；限购宽松分 = 100 −
          （限额 ≤100 元或暂停申购的场外基金占比）。<b className="text-zinc-200">温度越高 = 市场越拥挤、越不该追</b>；
          冰点反而是好买点的味道。灵感来自「纳纳小助手」的溢价×限购思路。
        </p>
      </Card>

      <Card className="p-5">
        <h3 className="mb-2 font-semibold text-zinc-100">溢价口径（重要）</h3>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-zinc-400">
          <li>溢价 = 场内最新价 ÷ <b className="text-zinc-200">最新披露净值</b> − 1。QDII 净值为 T-1 美股收盘口径，当晚 20:00 后更新</li>
          <li>「实时」溢价 = 浏览器直连腾讯行情取场内价 ÷ 上述净值，<b>未做 IOPV 与汇率实时修正</b>——A股盘中若人民币波动大，实际溢价有小幅误差</li>
          <li>「收盘」溢价 = 当日收盘价 ÷ 当日净值（对齐交易日），用于历史分位计算</li>
          <li>LOF 流动性差，场内价可能失真；表中 30/90/365 分位基于各自上市以来的溢价序列</li>
        </ul>
      </Card>

      <Card className="p-5">
        <h3 className="mb-2 font-semibold text-zinc-100">数据源与更新机制</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <tbody className="divide-y divide-zinc-800/60">
              {[
                ["场外限额/费率", "天天基金 F10（fundf10.eastmoney.com）", "每日快照存档，自动对比生成「限额风向」"],
                ["场外净值/状态", "蛋卷基金 djapi", "净值历史 + 申购/赎回状态"],
                ["场内行情/日K", "东方财富 push2his", "ETF/LOF 收盘价与实时行情"],
                ["指数长历史", "东方财富 push2his（100.SPX 自 1986、100.NDX 自 1991、100.NDX100 自 2019）", "长历史统计与回测底座"],
                ["标普500 PE", "multpl.com（Shiller 口径月度）", "估值分位"],
                ["实时行情", "腾讯 qt.gtimg.cn（浏览器直连）", "页面打开时的实时溢价"],
              ].map(([a, b, c]) => (
                <tr key={a}>
                  <td className="py-2 pr-3 align-top text-xs whitespace-nowrap text-zinc-300">{a}</td>
                  <td className="py-2 pr-3 align-top text-xs text-zinc-500">{b}</td>
                  <td className="py-2 align-top text-xs text-zinc-600">{c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-zinc-500">
          更新机制：GitHub Actions 每晚北京时间 20:00 / 21:00 抓取并生成静态 JSON 提交回仓库（QDII 净值晚间披露后的窗口），
          再由 Pages 工作流构建发布。某天抓取失败时，站点继续展示最近一次成功的数据——仓库历史里永远有底。
        </p>
      </Card>

      <Card className="p-5">
        <h3 className="mb-2 font-semibold text-zinc-100">回测口径</h3>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-zinc-400">
          <li>基金回测用<b className="text-zinc-200">净值</b>（已含管理费托管费，未计申购赎回费）；指数回测用<b className="text-zinc-200">收盘价</b>（不含任何费用）</li>
          <li>持有 N 个交易日 = 信号日收盘买入、N 日后收盘卖出；RSI/MA/回撤等指标只用当日及以前数据，无未来函数</li>
          <li>样本 &lt;30 的规则灰显——8 个样本的 100% 胜率毫无意义</li>
          <li>回测在浏览器端实时计算，与 Python 端 backtest.py 同口径，参数随便调</li>
        </ul>
      </Card>

      <Card className="p-5">
        <h3 className="font-semibold text-zinc-100">免责声明</h3>
        <p className="mt-2 text-xs leading-relaxed text-zinc-500">
          本站为开源技术统计工具，所有数据来自公开渠道，可能存在延迟或错误；限额、费率以基金公司与销售渠道为准。
          本站不构成任何投资建议，历史统计不代表未来表现，据此操作风险自负。投资有风险，入市需谨慎。
        </p>
      </Card>
    </div>
  );
}
