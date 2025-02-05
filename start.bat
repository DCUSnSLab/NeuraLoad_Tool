@echo off
echo Setting up Python environment...
python -m venv venv
call venv\Scripts\activate

echo Installing required packages...
pip install --upgrade pip
pip install pyqt5 pyqtgraph pyserial

echo Installation complete!

:: tool.py 실행
if exist tool.py (
    echo Launching tool.py...
    start python tool.py
) else (
    echo tool.py not found. Please create the file first.
)

pause
