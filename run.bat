@echo off
REM Claude Code Notch for Windows Launcher

echo Starting Claude Code Notch for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements...
    python -m pip install -r requirements.txt
)

REM Run the application
python src\main.py

pause
