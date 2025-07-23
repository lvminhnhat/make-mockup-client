@echo off
:: Phiên bản tối giản để khởi động nhanh
setlocal

:: Bỏ qua tạo thư mục nếu đã tồn tại
if not exist "downloads" mkdir downloads >nul
if not exist "statics\uploads" mkdir statics\uploads >nul
if not exist "statics\output" mkdir statics\output >nul

:: Kích hoạt môi trường ảo (nếu có)
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat" >nul
)

:: Chạy worker với thông báo tối giản
echo [SYSTEM] Đang khởi động worker...
echo [SYSTEM] Nhấn Ctrl+C để dừng
python worker.py

endlocal
