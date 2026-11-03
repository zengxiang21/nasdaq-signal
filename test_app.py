"""无头验证 app.py 全流程（不依赖浏览器）"""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=180)
at.run()

print("== 异常检查 ==")
if at.exception:
    for e in at.exception:
        print("EXCEPTION:", e.value)
    raise SystemExit(1)
print("无异常 ✅")

print("== 标题 ==", at.title[0].value if at.title else None)
print("== metric 数量 ==", len(at.metric))
for m in at.metric[:12]:
    print("  ", m.label, "=", m.value)
print("== tabs ==", len(at.tabs))
print("== dataframe 数量 ==", len(at.dataframe))
print("== plotly 图表数量 ==", len(at.get("plotly_chart")))
