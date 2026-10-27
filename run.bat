@echo off
echo Starting InvestIQ with project virtual environment (.venv)...
if exist .venv\Scripts\python.exe (
    .\.venv\Scripts\python.exe -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause
