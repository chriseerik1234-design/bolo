@echo off
title Lesson 1 - MAKING THE COMPUTER TALK
cd /d "%~dp0"
cls
echo.
echo   LESSON 1: MAKING THE COMPUTER TALK
echo   =====================================================
echo.
echo   This runs the file:   learn\01_say.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\01_say.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: add a line that says your own name
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\01_say.bolo"
