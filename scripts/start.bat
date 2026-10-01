@echo off
chcp 65001 >nul
title StudyBuddy 学习助手
cd /d "%~dp0.."

echo ==============================================
echo   StudyBuddy 学习助手 - 一键启动
echo ==============================================

where go >nul 2>nul
if errorlevel 1 (
    echo [提示] 未检测到 Go 环境，将尝试直接运行已编译的 dist\studybuddy.exe
) else (
    echo [1/2] 编译中...
    set CGO_ENABLED=0
    set GOPROXY=https://goproxy.cn,direct
    if not exist dist mkdir dist
    go build -ldflags "-s -w" -o dist\studybuddy.exe .\cmd\studybuddy
    if errorlevel 1 (
        echo [错误] 编译失败，请检查上方输出。
        pause
        exit /b 1
    )
)

if not exist dist\studybuddy.exe (
    echo [错误] 未找到 studybuddy.exe，请先安装 Go 或手动编译。
    pause
    exit /b 1
)

echo [2/2] 启动服务，浏览器访问 http://localhost:8080
echo       按 Ctrl+C 停止服务。
echo ==============================================
start "" http://localhost:8080
dist\studybuddy.exe
pause
