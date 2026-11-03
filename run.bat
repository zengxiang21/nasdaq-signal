@echo off
rem 启动 Streamlit 仪表盘
cd /d %~dp0
python -m streamlit run app.py
pause
