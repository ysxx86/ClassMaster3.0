@echo off
chcp 65001 >nul
echo ========================================
echo 智能导入诊断 - 重启服务器
echo ========================================
echo.
echo 正在停止现有服务器进程...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq server.py*" 2>nul
timeout /t 2 >nul
echo.
echo 正在启动服务器...
start "ClassMaster Server" python server.py
timeout /t 3 >nul
echo.
echo 服务器已启动！
echo.
echo 现在可以：
echo 1. 在浏览器中测试导入功能
echo 2. 查看实时日志（按任意键继续）
echo.
pause
echo.
echo ========================================
echo 实时日志输出（按 Ctrl+C 停止）
echo ========================================
echo.
powershell -Command "Get-Content logs\root_server.log -Wait -Tail 50"
