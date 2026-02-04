@echo off
echo ====================================
echo Running Database Migration
echo ====================================
cd /d D:\Development\altayar\MobileApp\backend
python fix_db_schema.py
echo.
echo ====================================
echo Migration Complete!
echo ====================================
pause
