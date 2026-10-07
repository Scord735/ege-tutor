@echo off
title EGE-TUTOR // STOP BACKEND

echo Stopping uvicorn processes...

taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq EGE-TUTOR // BACKEND*" 2>nul

echo.
echo Done.
echo.
pause