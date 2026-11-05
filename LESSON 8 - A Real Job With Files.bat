@echo off
title Lesson 8 - A REAL JOB WITH 08_real_job.boloS
cd /d "%~dp0"
cls
echo.
echo   LESSON 8: A REAL JOB WITH 08_real_job.boloS
echo   =====================================================
echo.
echo   This runs the file:   learn\08_real_job.bolo
echo.
echo   -----------------------------------------------------
call "%~dp0bolo.cmd" "learn\08_real_job.bolo"
echo.
echo   -----------------------------------------------------
echo   TRY THIS: count how many files have the extension txt
echo   -----------------------------------------------------
echo.
echo   Press any key to open the lesson in Notepad and change it.
pause >nul
start "" notepad "%~dp0learn\08_real_job.bolo"
