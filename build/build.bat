@echo off
chcp 65001 >nul
title 功率器件参数提取系统 - 打包工具

cd /d "%~dp0"

echo ==========================================
echo   功率器件参数提取系统 - 便携版打包
echo ==========================================
echo.
echo 此脚本将生成 Windows 便携版，用户解压后双击即可使用。
echo 预计耗时: 5-15 分钟（取决于网络速度）
echo.

python build_portable.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo 打包成功！请查看项目根目录下的 zip 文件。
pause
