@echo off
echo ========================================
echo Starting Photoshop Mockup Client
echo ========================================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and add it to your PATH
    pause
    exit /b 1
)

:: Get the current directory
set PROJECT_DIR=%~dp0

:: Check if virtual environment exists
if not exist "%PROJECT_DIR%venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call "%PROJECT_DIR%venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

:: Create necessary directories
if not exist "downloads" mkdir downloads
if not exist "statics\uploads" mkdir statics\uploads
if not exist "statics\output" mkdir statics\output

echo.
echo Starting worker process...
echo Worker will process tasks from the server
echo Press Ctrl+C to stop the worker
python worker.py
goto end

:end
echo.
echo Goodbye!
pause
