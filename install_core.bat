@echo off
echo ====================================
echo Installing Core Backend Dependencies
echo ====================================
cd /d D:\Development\altayar\MobileApp\backend

echo.
echo Installing core packages (skipping pillow for now)...
echo.

pip install fastapi==0.109.0
pip install uvicorn==0.27.0
pip install sqlalchemy==2.0.25
pip install pydantic==2.5.3
pip install pydantic-settings==2.1.0
pip install python-dotenv==1.0.0
pip install python-jose==3.3.0
pip install passlib==1.7.4
pip install bcrypt==4.1.3
pip install python-multipart==0.0.6
pip install alembic==1.13.1

echo.
echo ====================================
echo Core packages installed!
echo Starting server...
echo ====================================
echo.

python server.py

pause
