@echo off
title My challenge
cd /d "%~dp0"
cls
echo.
echo   YOUR CHALLENGE - learn\challenges\myjob.bolo
echo   =====================================================
echo.
echo   The job descriptions are in:  learn\challenges\README.md
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\challenges\myjob.bolo"
echo.
echo   -----------------------------------------------------
echo.
echo   Press any key to open myjob.bolo in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\challenges\myjob.bolo"
