@echo off
setlocal
set "HERE=%~dp0"

rem The Microsoft Store ships a fake "python.exe" alias, so check that it runs.
python -c "import sys" >nul 2>nul
if errorlevel 1 goto fallback

python "%HERE%bolo.py" %*
exit /b %ERRORLEVEL%

:fallback
set "FALLBACK=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%FALLBACK%" goto missing

"%FALLBACK%" "%HERE%bolo.py" %*
exit /b %ERRORLEVEL%

:missing
echo Python 3 is required but was not found.
echo Install it with:  winget install -e --id Python.Python.3.13
exit /b 9009
