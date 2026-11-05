@echo off
title Lesson 4 - MAKING CHOICES
cd /d "%~dp0"
cls
echo.
echo   LESSON 4: MAKING CHOICES
echo   =====================================================
echo.
echo   This runs the file:   learn\04_choices.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\04_choices.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: change age to 20 and run this again
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\04_choices.bolo"
