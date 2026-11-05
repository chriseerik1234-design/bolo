@echo off
title Lesson 7 - YOUR OWN TRICKS
cd /d "%~dp0"
cls
echo.
echo   LESSON 7: YOUR OWN TRICKS
echo   =====================================================
echo.
echo   This runs the file:   learn\07_recipes.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\07_recipes.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: write a trick called shout that makes capitals
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\07_recipes.bolo"
