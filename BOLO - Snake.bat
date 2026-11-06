@echo off
setlocal
cd /d "%~dp0"
set "HERE=%~dp0"
set "APP=%HERE%examples\snake_app.bolo"

rem pythonw runs the game without a black console window behind it.
pythonw -c "import sys" >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%HERE%bolo.py" "%APP%"
  exit /b 0
)

rem No pythonw? Use python and keep the window open if something goes wrong.
python -c "import sys" >nul 2>nul
if not errorlevel 1 (
  python "%HERE%bolo.py" "%APP%"
  if errorlevel 1 pause
  exit /b %ERRORLEVEL%
)

set "FALLBACKW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
set "FALLBACK=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

if exist "%FALLBACKW%" (
  start "" "%FALLBACKW%" "%HERE%bolo.py" "%APP%"
  exit /b 0
)

if not exist "%FALLBACK%" goto missing
"%FALLBACK%" "%HERE%bolo.py" "%APP%"
if errorlevel 1 pause
exit /b %ERRORLEVEL%

:missing
echo Python 3 is required but was not found.
echo Install it with:  winget install -e --id Python.Python.3.13
pause
exit /b 9009
