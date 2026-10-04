@echo off
cd /d %~dp0
call venv\Scripts\activate
python scraper_tradicional_hasta_ayer.py
pause