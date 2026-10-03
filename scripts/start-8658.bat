@echo off
chcp 65001 >nul
title StudyBuddy 学习助手 (端口 8658)
cd /d "%~dp0.."

rem ============================================================
rem  独立启动 StudyBuddy（端口 8658）
rem  与 start.bat 的区别：不重新编译、不自动开浏览器。
rem  二进制已由开发流程编译验证过，这里只负责把它跑起来，
rem  这样进程归这个窗口管，不会被开发工具的后台任务回收掉。
rem ============================================================

if not exist dist\studybuddy.exe (
    echo [错误] 未找到 dist\studybuddy.exe
    echo        请先在项目根目录执行：go build -o dist\studybuddy.exe ./cmd\studybuddy
    pause
    exit /b 1
)

set STUDYBUDDY_PORT=8658
set GIN_MODE=release

echo ==============================================
echo   StudyBuddy 学习助手
echo   访问地址 : http://localhost:8658
echo   停止服务 : 关闭本窗口，或按 Ctrl+C
echo ==============================================
echo.

dist\studybuddy.exe

echo.
echo [服务已停止]
pause
