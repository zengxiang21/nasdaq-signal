@echo off
rem 一键启动：更新数据 -> 构建前端 -> 本机静态服务（Tailscale 内网可访问）
rem 浏览器打开 http://localhost:8511/（局域网用本机 Tailscale IP:8511）
cd /d %~dp0

echo == [1/3] 更新数据并导出 JSON ==
python scripts/export_web_data.py --update
if errorlevel 1 goto :err

echo == [2/3] 构建前端 ==
cd web
call npm run build || goto :err

echo == [3/3] 启动本地服务 http://localhost:8511/ ==
call npx vite preview --host --port 8511
goto :eof

:err
echo.
echo 启动失败，请检查上方报错（首次使用先: pip install -r requirements.txt ^&^& cd web ^&^& npm install）
pause
