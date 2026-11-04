@echo off
rem Copyright 2026 Aayush Kadam
rem SPDX-License-Identifier: Apache-2.0
setlocal DisableDelayedExpansion
where py >nul 2>&1
if not errorlevel 1 goto py
python "%~dp0launch_observatory.py" %*
goto done
:py
py -3 "%~dp0launch_observatory.py" %*
:done
set "B2_EXIT=%ERRORLEVEL%"
if not "%B2_EXIT%"=="0" pause
exit /b %B2_EXIT%
