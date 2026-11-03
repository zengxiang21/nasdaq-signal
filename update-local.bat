@echo off
rem 每晚本地重建：抓数据 + 重建前端，让 Tailscale 本机站与 GitHub Pages 同步新鲜
cd /d "C:\Users\Administrator\nasdaq-signal"
python scripts/export_web_data.py --update
cd web
call npm run build
