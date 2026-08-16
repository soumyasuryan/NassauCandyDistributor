@echo off
REM Start the Nassau Candy Dashboard
REM This script activates the virtual environment and starts the Streamlit app

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Run the Streamlit app
echo Starting Nassau Candy Dashboard...
streamlit run src/app.py
pause
