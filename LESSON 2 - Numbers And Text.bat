@echo off
title Lesson 2 - NUMBERS AND TEXT
cd /d "%~dp0"
cls
echo.
echo   LESSON 2: NUMBERS AND TEXT
echo   =====================================================
echo.
echo   This runs the file:   learn\02_numbers.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\02_numbers.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: change 10 % 3 to 17 % 5 and guess first
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\02_numbers.bolo"
