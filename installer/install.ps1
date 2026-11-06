#Requires -Version 5.1
<#
    Bolo for Windows - the internet installer.

    It downloads one zip, puts Bolo in your own user folder, adds Start Menu
    and Desktop shortcuts, and makes the "bolo" command available in a new
    terminal. It does not need administrator rights and does not change
    anything outside:

        %LOCALAPPDATA%\Programs\Bolo      the program
        %LOCALAPPDATA%\Bolo               your progress and practice files
        Start Menu > Bolo
        Desktop shortcuts (optional)

    Run it from a web page, the usual way:

        irm https://github.com/chriseerik1234-design/bolo/releases/latest/download/install.ps1 | iex

    Or download it and run it, which allows options:

        powershell -ExecutionPolicy Bypass -File install.ps1
        powershell -ExecutionPolicy Bypass -File install.ps1 -NoDesktopShortcut
        powershell -ExecutionPolicy Bypass -File install.ps1 -ZipPath .\Bolo-Windows.zip

    Nothing is sent anywhere except the one download you asked for.
#>
[CmdletBinding()]
param(
    # Where Bolo-Windows.zip lives. Change this once, before publishing.
    [string]$Url = "https://github.com/chriseerik1234-design/bolo/releases/latest/download/Bolo-Windows.zip",

    # Or install from a zip already on this computer (for testing).
    [string]$ZipPath = "",

    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\Bolo"),

    [switch]$NoDesktopShortcut,
    [switch]$NoShortcuts,
    [switch]$NoPath,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Say([string]$Text, [string]$Color = "Gray") {
    Write-Host $Text -ForegroundColor $Color
}

function Step([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function New-Shortcut([string]$Path, [string]$Target, [string]$WorkingDir, [string]$Arguments = "") {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Target
    $shortcut.WorkingDirectory = $WorkingDir
    if ($Arguments) { $shortcut.Arguments = $Arguments }
    $shortcut.IconLocation = "$Target,0"
    $shortcut.Description = "Bolo - a small, friendly programming language"
    $shortcut.Save()
}

Write-Host ""
Write-Host "  Bolo for Windows" -ForegroundColor Green
Write-Host "  a small, friendly programming language" -ForegroundColor DarkGray

if (-not $env:LOCALAPPDATA) {
    throw "This installer is for Windows."
}

# --- 1. get the zip -------------------------------------------------------
$tempRoot = Join-Path $env:TEMP ("bolo-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
$zip = Join-Path $tempRoot "Bolo-Windows.zip"

try {
    if ($ZipPath) {
        Step "Using the zip on this computer"
        if (-not (Test-Path $ZipPath)) { throw "No file at: $ZipPath" }
        Copy-Item (Resolve-Path $ZipPath).Path $zip -Force
    }
    else {
        Step "Downloading Bolo"
        Say "  from $Url"
        if ($Url -match "YOUR-NAME") {
            throw @"
The download address has not been set yet.

If you built Bolo yourself, install the local zip instead:
    powershell -ExecutionPolicy Bypass -File installer\install.ps1 -ZipPath installer\Bolo-Windows.zip

If you are publishing Bolo, edit `$Url at the top of installer\install.ps1
(and the link in index.html) to the real address.
"@
        }
        try {
            Invoke-WebRequest -Uri $Url -OutFile $zip -UseBasicParsing
        }
        catch {
            throw "Could not download Bolo from $Url`n$($_.Exception.Message)"
        }
    }

    if (-not (Test-Path $zip) -or (Get-Item $zip).Length -lt 100000) {
        throw "The download looks empty or incomplete. Try again."
    }

    # --- 2. stop an older copy politely ----------------------------------
    foreach ($name in @("BoloLearn", "BoloChat", "bolo")) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }

    # --- 3. unpack into the user's program folder -------------------------
    Step "Installing to $InstallDir"
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    try {
        Expand-Archive -Path $zip -DestinationPath $InstallDir -Force
    }
    catch {
        throw "Could not unpack the download: $($_.Exception.Message)"
    }

    $learnExe = Join-Path $InstallDir "BoloLearn.exe"
    $chatExe = Join-Path $InstallDir "BoloChat.exe"
    $boloExe = Join-Path $InstallDir "bolo.exe"
    if (-not (Test-Path $learnExe) -or -not (Test-Path $boloExe)) {
        throw "The download did not contain a complete Bolo. Try downloading again."
    }
    Say "  BoloLearn.exe, BoloChat.exe and bolo.exe are in place." "Green"

    # --- 4. shortcuts ------------------------------------------------------
    if (-not $NoShortcuts) {
    Step "Adding shortcuts"
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Bolo"
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
    New-Shortcut (Join-Path $startMenu "Bolo Learn.lnk") $learnExe $InstallDir
    New-Shortcut (Join-Path $startMenu "Bolo Chat.lnk") $chatExe $InstallDir
    New-Shortcut (Join-Path $startMenu "Bolo Tasks.lnk") $boloExe $InstallDir `
        "`"$InstallDir\examples\tasks_app.bolo`""
    Say "  Start Menu > Bolo" "Green"

    if (-not $NoDesktopShortcut) {
        $desktop = [Environment]::GetFolderPath("Desktop")
        if ($desktop) {
            New-Shortcut (Join-Path $desktop "Bolo Learn.lnk") $learnExe $InstallDir
            New-Shortcut (Join-Path $desktop "Bolo Chat.lnk") $chatExe $InstallDir
            Say "  Desktop: Bolo Learn, Bolo Chat" "Green"
        }
    }
    }

    # --- 5. the "bolo" command in new terminals ---------------------------
    if (-not $NoPath) {
        Step "Adding the bolo command to your user PATH"
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $parts = @()
        if ($userPath) { $parts = $userPath -split ";" | Where-Object { $_ } }
        if ($parts -notcontains $InstallDir) {
            $newPath = (($parts + $InstallDir) -join ";")
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Say "  Open a new terminal, then run:  bolo learn\01_say.bolo" "Green"
        }
        else {
            Say "  Already there."
        }
    }

    # --- 6. an uninstaller -------------------------------------------------
    if (-not $NoShortcuts) {
    $uninstall = Join-Path $InstallDir "uninstall.ps1"
    $uninstallText = @'
param([switch]$KeepData)
$ErrorActionPreference = "SilentlyContinue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($name in @("BoloLearn", "BoloChat", "bolo")) {
    Get-Process -Name $name | Stop-Process -Force
}
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Bolo"
Remove-Item $startMenu -Recurse -Force
$desktop = [Environment]::GetFolderPath("Desktop")
Remove-Item (Join-Path $desktop "Bolo Learn.lnk") -Force
Remove-Item (Join-Path $desktop "Bolo Chat.lnk") -Force
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    $parts = $userPath -split ";" | Where-Object { $_ -and $_ -ne $here }
    [Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "User")
}
if (-not $KeepData) {
    Remove-Item (Join-Path $env:LOCALAPPDATA "Bolo") -Recurse -Force
}
Set-Location $env:TEMP
Remove-Item $here -Recurse -Force
Write-Host "Bolo was removed." -ForegroundColor Green
'@
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($uninstall, ($uninstallText -replace "`r?`n", "`r`n"), $utf8)
    New-Shortcut (Join-Path $startMenu "Uninstall Bolo.lnk") `
        "powershell.exe" $InstallDir `
        "-NoProfile -ExecutionPolicy Bypass -File `"$uninstall`""
    }
    Write-Host ""
    Write-Host "  Bolo is installed." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Learn:  Start Menu > Bolo > Bolo Learn"
    Write-Host "  Chat:   Start Menu > Bolo > Bolo Chat"
    Write-Host "  Tasks:  Start Menu > Bolo > Bolo Tasks"
    Write-Host "  Code:   bolo learn\01_say.bolo   (in a new terminal)"
    Write-Host ""
    Write-Host "  The AI parts need Ollama: https://ollama.com" -ForegroundColor DarkGray
    Write-Host "  Everything else works without it." -ForegroundColor DarkGray
    Write-Host ""

    if (-not $NoLaunch) {
        Start-Process -FilePath $learnExe -WorkingDirectory $InstallDir
    }
}
catch {
    Write-Host ""
    Write-Host "Install did not finish." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Nothing outside your user folder was touched." -ForegroundColor DarkGray
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
