@echo off
cd /d %~dp0
call venv\Scripts\activate
python scraper_tradicional.py
pause