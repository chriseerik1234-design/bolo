@echo off
title Lesson 5 - LISTS, AND THE WORD THEN
cd /d "%~dp0"
cls
echo.
echo   LESSON 5: LISTS, AND THE WORD THEN
echo   =====================================================
echo.
echo   This runs the file:   learn\05_lists.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\05_lists.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: add banana to the list and say its length
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\05_lists.bolo"
