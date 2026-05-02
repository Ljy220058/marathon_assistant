@echo off
setlocal
cd /d "%~dp0"
echo Starting Chainlit app from %cd%
chainlit run app_chainlit.py -w
set "EXIT_CODE=%errorlevel%"
echo Batch script finished with error level %EXIT_CODE%
exit /b %EXIT_CODE%
