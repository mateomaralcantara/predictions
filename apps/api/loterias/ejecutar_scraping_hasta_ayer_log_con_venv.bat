@echo off
cd /d %~dp0
call venv\Scripts\activate
echo ==== EJECUCIÓN: %date% %time% ==== >> scraping_log.txt
python scraper_tradicional_hasta_ayer.py >> scraping_log.txt 2>&1
echo. >> scraping_log.txt
pause