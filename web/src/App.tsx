import { NavLink, Route, Routes } from "react-router-dom";
import About from "./pages/About";
import Backtest from "./pages/Backtest";
import History from "./pages/History";
import Limits from "./pages/Limits";
import Premium from "./pages/Premium";
import Today from "./pages/Today";
import Tools from "./pages/Tools";

const NAV = [
  { to: "/", label: "今日", end: true },
  { to: "/premium", label: "场内溢价" },
  { to: "/limits", label: "场外限额" },
  { to: "/history", label: "长历史" },
  { to: "/backtest", label: "胜率回测" },
  { to: "/tools", label: "工具" },
  { to: "/about", label: "说明" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 pt-3 pb-2">
          <div className="flex items-baseline justify-between gap-4">
            <NavLink to="/" className="text-base font-bold text-zinc-100">
              📈 纳指 / 标普500 买入信号
            </NavLink>
            <span className="hidden text-[11px] text-zinc-600 sm:block">
              口径全透明 · 历史统计不构成投资建议
            </span>
          </div>
          <nav className="-mx-1 flex gap-1 overflow-x-auto px-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm whitespace-nowrap transition-colors ${
                    isActive
                      ? "bg-zinc-800 font-medium text-zinc-100"
                      : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Today />} />
          <Route path="/premium" element={<Premium />} />
          <Route path="/limits" element={<Limits />} />
          <Route path="/history" element={<History />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>

      <footer className="border-t border-zinc-900 py-6 text-center text-[11px] leading-relaxed text-zinc-600">
        数据源：天天基金 F10 · 蛋卷基金 · 东方财富 · multpl ｜
        本站为历史统计工具，不构成投资建议，历史胜率不代表未来表现
      </footer>
    </div>
  );
}
