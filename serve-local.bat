@echo off
rem 常驻静态服务：手机经 Tailscale 访问 http://100.111.139.1:8511/
rem 由计划任务 nasdaq-signal-web 在登录时静默启动
cd /d "C:\Users\Administrator\nasdaq-signal\web"
"C:\Program Files\nodejs\node.exe" node_modules\vite\bin\vite.js preview --host --port 8511
