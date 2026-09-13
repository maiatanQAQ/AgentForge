@echo off
setlocal
chcp 936 >nul
title AgentForge — planner(Codex) / worker(ZCode) / reviewer(Codex)

rem ------------------------------------------------------------------
rem Repo root = this file's directory
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

rem --- omnigent venv python (uv tools default location) ---
set "PY=%APPDATA%\uv\tools\omnigent\Scripts\python.exe"
if not exist "%PY%" (
  echo [X] omnigent venv python not found:
  echo     %PY%
  echo     Install omnigent first:  uv tool install omnigent
  pause
  exit /b 1
)

:menu
cls
echo ==================================================
echo   AgentForge v0.1.1
echo   planner=Codex   worker=ZCode(ACP)   reviewer=Codex
echo ==================================================
echo.
echo   [1]  运行示例任务 —— 修复 calc.js（约 2-5 分钟）
echo   [2]  运行自定义任务（输入工作目录 + 任务描述）
echo   [3]  环境自检
echo   [4]  退出
echo.
choice /c 1234 /n /m "请按数字选择: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto :check
if errorlevel 2 goto :custom
goto :demo

:demo
call :stopdaemon
echo.
echo [1/3] 重置示例工作区（恢复带 bug 的 calc.js）...
copy /y "%ROOT%\examples\phase2-demo\workspace\calc.js.buggy" "%ROOT%\examples\phase2-demo\workspace\calc.js" >nul
set "WORKDIR=%ROOT%\examples\phase2-demo\workspace"
set "PROMPT=Fix the bug in calc.js in this workspace: the add() function currently subtracts instead of adding. Acceptance contract: running 'node calc.js 2 3' prints exactly 5, and 'node calc.js -1 1' prints 0."
goto :run

:custom
call :stopdaemon
echo.
set /p "WORKDIR=工作目录（绝对路径，任务在此目录内执行）: "
if "%WORKDIR%"=="" echo [X] 未输入目录 & pause & goto :menu
if not exist "%WORKDIR%" echo [X] 目录不存在: %WORKDIR% & pause & goto :menu
set /p "PROMPT=任务描述（单行，务必包含可验证的验收契约）: "
if "%PROMPT%"=="" echo [X] 未输入任务 & pause & goto :menu

:run
echo.
echo [2/3] 启动三角色流水线: planner(Codex) -^> worker(ZCode) -^> reviewer(Codex)
echo       本窗口持续输出进度，跑完自动返回菜单。预计 2-5 分钟。
echo       会话链接（可在浏览器打开旁观）见下方。
echo.
cd /d "%ROOT%"
"%PY%" scripts\run_workflow.py workflows\codex-plans-zcode-executes.yaml --cwd "%WORKDIR%" --prompt "%PROMPT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [OK] 流水线完成（退出码 0）。请检查上方 reviewer 是否 PASS，
  echo      并到工作目录查看实际改动。
) else (
  echo [X] 流水线失败（退出码 %RC%）。
  echo     排障: docs\architecture.md 末尾的失败模式表；重跑前先选菜单 [3] 自检。
)
echo.
pause
goto :menu

:check
echo.
echo [环境自检]
if exist "%ROOT%\.env" (echo   [OK] .env 存在) else (echo   [!!] .env 缺失 —— 复制 .env.example 为 .env 并填写 OMNIGENT_CODEX_PATH)
if exist "%ROOT%\adapters\zcode-acp\node_modules\zcode-acp-server\dist\index.js" (echo   [OK] ACP 桥已本地安装) else (echo   [!!] 桥未本地安装 —— 在 adapters\zcode-acp 目录执行: npm install zcode-acp-server)
where codex >nul 2>&1 && (echo   [OK] codex 可从 PATH 解析) || (echo   [!!] codex 不在 PATH —— 检查 .env 的 OMNIGENT_CODEX_PATH（桌面版升级后路径会变）)
"%PY%" -c "import omnigent" >nul 2>&1 && (echo   [OK] omnigent 可导入) || (echo   [X] omnigent 不可导入 —— venv python 路径不对，重装: uv tool install omnigent)
node --version >nul 2>&1 && (echo   [OK] node 存在) || (echo   [!!] node 不在 PATH —— ZCode/桥需要 Node ^>= 22)
echo.
pause
goto :menu

:stopdaemon
where omnigent >nul 2>&1 && omnigent stop >nul 2>&1
exit /b 0
