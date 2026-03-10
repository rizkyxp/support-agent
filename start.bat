@echo off
echo Starting Support Agent Control Panel...

:: Check if python is available
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: Check if pip is available
where pip >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip is not installed or not in PATH.
    pause
    exit /b 1
)

echo Installing requirements...
pip install -r requirements.txt

echo Starting the Web UI Control Panel...
echo Open your browser at http://localhost:8000 to use the local control panel.
echo.
python -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000 --reload
pause
