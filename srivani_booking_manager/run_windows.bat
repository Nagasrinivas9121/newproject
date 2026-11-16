@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 app.py
    goto done
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python app.py
    goto done
)

echo.
echo =======================================================================
echo [ERROR] Python was not found on your system PATH.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo Make sure to check the box "Add Python to PATH" during installation.
echo =======================================================================
echo.
pause
exit /b 1

:done
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%.
    pause
)
