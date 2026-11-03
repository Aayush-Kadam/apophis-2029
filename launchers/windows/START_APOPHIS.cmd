@echo off
rem Copyright 2026 Aayush Kadam
rem SPDX-License-Identifier: Apache-2.0
setlocal DisableDelayedExpansion
where py >nul 2>&1
if not errorlevel 1 goto use_py
where python >nul 2>&1
if not errorlevel 1 goto use_python
echo Python 3 is required. Install it from https://www.python.org/ and try again.
echo This launcher does not install Python or any packages.
pause
exit /b 1
:use_py
py -3 "%~dp0launch_apophis.py" %*
set "APOPHIS_EXIT=%ERRORLEVEL%"
goto finished
:use_python
python "%~dp0launch_apophis.py" %*
set "APOPHIS_EXIT=%ERRORLEVEL%"
:finished
if not "%APOPHIS_EXIT%"=="0" pause
exit /b %APOPHIS_EXIT%
