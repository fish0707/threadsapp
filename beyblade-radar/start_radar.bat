@echo off
rem Beyblade X 雷達 —— 家裡電腦常駐啟動檔(Windows)
rem 雙擊執行即可;程式意外結束會在 10 秒後自動重啟。要停止就直接關掉這個視窗。
chcp 65001 > nul
set PYTHONUTF8=1
cd /d "%~dp0"
title Beyblade Radar

set PY=python
where python > nul 2> nul || set PY=py

:loop
%PY% run.py
echo.
echo [start_radar] 雷達結束了,10 秒後自動重啟...(要停止請關掉這個視窗)
timeout /t 10 /nobreak > nul
goto loop
