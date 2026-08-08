@echo off
echo Starting E.V. Agent...

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found in 'venv'. Ensure dependencies are installed.
)

REM Run the agent in voice mode
python main.py --voice
pause
