@echo off
REM Use Python directly with your virtual environment
REM Example: split_pdf.bat input.pdf --dpi 100 --quality 50
.venv\Scripts\python.exe split_pdf.py %*
