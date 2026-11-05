@echo off
title Lesson 6 - REPEATING THINGS
cd /d "%~dp0"
cls
echo.
echo   LESSON 6: REPEATING THINGS
echo   =====================================================
echo.
echo   This runs the file:   learn\06_repeat.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\06_repeat.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: print the numbers 1 to 10 with a for loop
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\06_repeat.bolo"
