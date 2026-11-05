@echo off
title Lesson 3 - BOXES WITH NAMES
cd /d "%~dp0"
cls
echo.
echo   LESSON 3: BOXES WITH NAMES
echo   =====================================================
echo.
echo   This runs the file:   learn\03_boxes.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\03_boxes.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: make a box called pet and say something about it
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\03_boxes.bolo"
