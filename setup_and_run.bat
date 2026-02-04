@echo off
echo ====================================
echo Installing Backend Dependencies
echo ====================================
cd /d D:\Development\altayar\MobileApp\backend

echo.
echo [1/2] Installing requirements...
pip install -r requirements.txt

echo.
echo [2/2] Starting server...
python server.py

pause
