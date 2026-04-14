@echo off
chcp 65001 >nul
echo ========================================
echo 安装 ReportLab PDF 生成库
echo ========================================
echo.
echo 正在安装 reportlab...
pip install reportlab
echo.
if %ERRORLEVEL% EQU 0 (
    echo ✓ ReportLab 安装成功！
) else (
    echo ✗ ReportLab 安装失败，请检查网络连接或手动安装
)
echo.
pause
