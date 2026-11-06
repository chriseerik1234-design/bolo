#Requires -Version 5.1
<#
    Build the downloadable Windows version of Bolo.

    What it makes, in installer\dist\ :
        BoloLearn.exe   the learning app (a window, no console)
        BoloChat.exe    Bolo Chat (a window, no console)
        bolo.exe        the language itself (a console program)
        learn\          the reading lessons and challenges
        examples\       finished programs
        ollama\         model recipes, for people who want the local AI
        README.md, HOW_TO_RUN.txt
        bolo.cmd        so "bolo file.bolo" works in a terminal

    ...and then packs all of it into installer\Bolo-Windows.zip, which is the
    one file you publish on the internet.

    Run it from PowerShell:
        powershell -ExecutionPolicy Bypass -File installer\build.ps1

    It creates a private virtual environment in installer\.build\venv, so
    PyInstaller never touches your normal Python. The first run downloads
    PyInstaller; later runs reuse it.
#>
[CmdletBinding()]
param(
    [string]$Python = "",
    [switch]$SkipTests,
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Root = Split-Path -Parent $Here
$BuildDir = Join-Path $Here ".build"
$DistDir = Join-Path $Here "dist"
$WorkDir = Join-Path $BuildDir "work"
$SpecDir = Join-Path $BuildDir "spec"
$VenvDir = Join-Path $BuildDir "venv"
$ZipPath = Join-Path $Here "Bolo-Windows.zip"

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Resolve-Python {
    if ($Python) {
        if (-not (Test-Path $Python)) { throw "No Python at: $Python" }
        return (Resolve-Path $Python).Path
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $known = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
    if (Test-Path $known) { return $known }
    throw "Python 3.10+ was not found. Install it from https://python.org, then run this again."
}

$PythonExe = Resolve-Python
Write-Host "Bolo installer build" -ForegroundColor Green
Write-Host "  project: $Root"
Write-Host "  python:  $PythonExe"

# --- 1. a private build environment ----------------------------------------
Write-Step "Preparing the build environment"
if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}
$Py = Join-Path $VenvDir "Scripts\python.exe"

& $Py -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) { throw "Could not update pip." }
& $Py -m pip install "pyinstaller>=6.11" --quiet
if ($LASTEXITCODE -ne 0) { throw "Could not install PyInstaller." }

# --- 2. the tests must still pass ------------------------------------------
if (-not $SkipTests) {
    Write-Step "Running the tests"
    $env:PYTHONIOENCODING = "utf-8"
    $env:BOLO_GUI_SILENT = "1"
    & $Py -m unittest discover -s (Join-Path $Root "tests") -q
    if ($LASTEXITCODE -ne 0) { throw "The tests failed. Fix them before building." }
}

# --- 3. clean, then build the three programs -------------------------------
Write-Step "Cleaning old output"
foreach ($folder in @($DistDir, $WorkDir, $SpecDir)) {
    if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $DistDir, $WorkDir, $SpecDir | Out-Null

$common = @(
    "--noconfirm", "--clean",
    "--onefile",
    "--distpath", $DistDir,
    "--workpath", $WorkDir,
    "--specpath", $SpecDir
)

Write-Step "Building bolo.exe (the language)"
& $Py -m PyInstaller @common --name bolo (Join-Path $Root "bolo.py")
if ($LASTEXITCODE -ne 0) { throw "Could not build bolo.exe." }

Write-Step "Building BoloLearn.exe (the learning app)"
& $Py -m PyInstaller @common --windowed --name BoloLearn (Join-Path $Root "bolo_app.py")
if ($LASTEXITCODE -ne 0) { throw "Could not build BoloLearn.exe." }

Write-Step "Building BoloChat.exe (the AI chat app)"
& $Py -m PyInstaller @common --windowed --name BoloChat (Join-Path $Root "bolo_chat.py")
if ($LASTEXITCODE -ne 0) { throw "Could not build BoloChat.exe." }

# --- 4. the friendly bits around the programs ------------------------------
Write-Step "Adding lessons, examples and launchers"
foreach ($item in @("learn", "examples", "ollama")) {
    $source = Join-Path $Root $item
    if (Test-Path $source) {
        Copy-Item $source -Destination $DistDir -Recurse -Force
    }
}
foreach ($file in @("README.md", "HOW_TO_RUN.txt")) {
    $source = Join-Path $Root $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $DistDir -Force
    }
}

function Write-TextFile([string]$Path, [string]$Text) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, ($Text -replace "`r?`n", "`r`n"), $utf8)
}

Write-TextFile (Join-Path $DistDir "bolo.cmd") @"
@echo off
"%~dp0bolo.exe" %*
"@

Write-TextFile (Join-Path $DistDir "Bolo Learn.bat") @"
@echo off
start "" "%~dp0BoloLearn.exe"
"@

Write-TextFile (Join-Path $DistDir "Bolo Chat.bat") @"
@echo off
start "" "%~dp0BoloChat.exe"
"@

Write-TextFile (Join-Path $DistDir "Bolo Tasks.bat") @"
@echo off
cd /d "%~dp0"
start "" "%~dp0bolo.exe" "%~dp0examples\tasks_app.bolo"
"@

Write-TextFile (Join-Path $DistDir "Start here.txt") @"
Bolo is ready.

  Double-click "Bolo Learn.bat" to learn the language.
  Double-click "Bolo Chat.bat"  to talk with the local AI.
  Double-click "Bolo Tasks.bat" to use a finished app written in Bolo.

The AI parts need Ollama from https://ollama.com. Everything else works
without it, including the whole language and the lessons.

In a terminal in this folder, run a file with:

    bolo learn\01_say.bolo

More words: README.md
"@

# --- 5. one zip to publish ------------------------------------------------
if (-not $NoZip) {
    Write-Step "Packing Bolo-Windows.zip"
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $DistDir, $ZipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )
    $sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
    Write-Host "  $ZipPath  ($sizeMb MB)" -ForegroundColor Green
}

Write-Step "Done"
Write-Host "  programs: $DistDir"
if (-not $NoZip) {
    Write-Host "  publish:  $ZipPath"
    Write-Host ""
    Write-Host "Next: put the zip on a web server or a GitHub release, then point"
    Write-Host "installer\install.ps1 and index.html at it. See"
    Write-Host "installer\README.md for the exact steps." -ForegroundColor Yellow
}
