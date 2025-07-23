@echo off
:: setup.bat - Cài đặt môi trường dự án
setlocal enabledelayedexpansion

echo.
echo ##################################################
echo #          CÀI ĐẶT MÔI TRƯỜNG DỰ ÁN             #
echo ##################################################
echo.

:: 1. Kiểm tra Python
echo [1/4] ðŸ”¥ Kiá»ƒm tra Python...
python --version 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python chÆ°a Ä‘Æ°á»£c cÃ i Ä‘áº·t hoáº·c khÃ´ng cÃ³ trong PATH
    echo Vui lÃ²ng cÃ i Ä‘áº·t Python 3.7+ tá»«: https://www.python.org/downloads/
    echo Sau Ä‘Ã³ thÃªm Python vÃ o PATH khi cÃ i Ä‘áº·t
    pause
    exit /b 1
)

:: 2. Táº¡o virtual environment
echo.
echo [2/4] ðŸ”¥ Táº¡o virtual environment...
if not exist ".venv\" (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: KhÃ´ng thá»ƒ táº¡o virtual environment
        pause
        exit /b 1
    )
    echo ÄÃ£ táº¡o thÃ nh cÃ´ng virtual environment
) else (
    echo Virtual environment Ä‘Ã£ tá»“n táº¡i (.venv)
)

:: 3. CÃ i Ä‘áº·t dependencies
echo.
echo [3/4] ðŸ”¥ CÃ i Ä‘áº·t thÆ° viá»‡n...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: KhÃ´ng thá»ƒ kÃch hoáº¡t virtual environment
    pause
    exit /b 1
)

pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: CÃ³ lá»—i khi cÃ i Ä‘áº·t thÆ° viá»‡n
    pause
    exit /b 1
)

:: 4. Táº¡o thÆ° má»¥c cáº§n thiáº¿t
echo.
echo [4/4] ðŸ”¥ Táº¡o thÆ° má»¥c...
if not exist "downloads" mkdir downloads
if not exist "logs" mkdir logs
if not exist "statics\uploads" mkdir statics\uploads
if not exist "statics\output" mkdir statics\output

echo.
echo ðŸŽ‰ CÃ i Ä‘áº·t hoÃ n táº¥t!
echo.
echo ðŸ”¥ Sá»­ dá»¥ng lá»‡nh sau Ä‘á»ƒ khá»Ÿi Ä‘á»™ng dá»± Ã¡n:
echo    start.bat
echo.
pause
endlocal
