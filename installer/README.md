# Building the internet installer

This folder turns the project into one file people can download and run on a
Windows machine that has **no Python installed**:

```
installer\Bolo-Windows.zip
```

It contains three programs built with PyInstaller:

| File | What it is |
|---|---|
| `BoloLearn.exe` | the learning app (a window) |
| `BoloChat.exe` | Bolo Chat (a window) |
| `bolo.exe` | the language itself (a console program) |
| `learn\`, `examples\`, `ollama\` | the course, sample programs, model recipes |
| `bolo.cmd` | makes `bolo file.bolo` work in a terminal |

## 1. Build it

From PowerShell in the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

What happens:

1. A private Python environment is created in `installer\.build\venv`.
2. PyInstaller is downloaded into it (the first run needs internet).
3. All 174 tests run. A failing test stops the build.
4. Three one-file programs are built into `installer\dist\`.
5. Lessons, examples, and launchers are copied in.
6. Everything is zipped to `installer\Bolo-Windows.zip`.

Useful switches:

```powershell
# skip the tests (not recommended)
... build.ps1 -SkipTests

# build the folder but do not zip it
... build.ps1 -NoZip

# use a specific Python
... build.ps1 -Python C:\Python313\python.exe
```

The build is reproducible: delete `installer\.build\` and `installer\dist\`
for a clean run.

## 2. Test it like a stranger would

```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1 `
  -ZipPath installer\Bolo-Windows.zip -NoLaunch
```

That installs into `%LOCALAPPDATA%\Programs\Bolo` exactly as the web installer
does. Check:

- Start Menu → Bolo → **Bolo Learn** opens. A lesson runs.
- Start Menu → Bolo → **Bolo Chat** opens. Chat mode answers if Ollama is
  running; code mode writes Bolo.
- In a **new** terminal: `bolo learn\01_say.bolo` works.
- Start Menu → Bolo → **Uninstall Bolo** removes it (keep your data if you
  prefer by running the generated `uninstall.ps1 -KeepData`).

The installed apps keep your progress in `%LOCALAPPDATA%\Bolo`, so
uninstalling the program does not throw away your code by accident.

## 3. Put it online

Upload two files from this folder to any static web host or a GitHub release:

```
Bolo-Windows.zip
install.ps1
```

For a GitHub release:

```powershell
gh release create v1.0 installer\Bolo-Windows.zip `
  --title "Bolo 1.0" `
  --notes "The first full release: loops, tables, try/catch, a chat app, and a one-command installer."
```

Then edit the address in **two** places:

1. `installer\install.ps1`, the `$Url` parameter near the top.
2. `installer\index.html`, the `#one-liner` text.

Example for a GitHub release:

```
https://github.com/chriseerik1234-design/bolo/releases/latest/download/Bolo-Windows.zip
```

The one-command installer is then:

```powershell
irm https://github.com/chriseerik1234-design/bolo/releases/latest/download/install.ps1 | iex
```

`install.ps1` refuses to run while the address still says `YOUR-NAME`, so a
half-published release fails with a clear message instead of downloading
something wrong. This repository is already published as
`chriseerik1234-design/bolo`, so the addresses above are live.

## 4. Host the page

`index.html`, `Bolo-Windows.zip`, and `install.ps1` sitting in the same folder
is a complete site. Any static host works: GitHub Pages, Netlify, Cloudflare
Pages, or a plain web server.

On GitHub Pages, publish this `installer\` folder (for example by copying its
three files into a `docs\` folder and enabling Pages for `docs\`).

The page uses no external fonts, scripts, or analytics. It makes no network
requests until someone clicks a download.

## How the installer behaves

- **No administrator rights.** Everything goes under the current user's
  `%LOCALAPPDATA%`.
- **One download.** It fetches the zip and nothing else.
- **Idempotent.** Running it again replaces the program but leaves
  `%LOCALAPPDATA%\Bolo` (progress and practice files) alone.
- **PATH is optional.** It adds the install folder to the *user* PATH so
  `bolo` works in a new terminal; a failure there does not stop the install.
- **Shortcuts.** Start Menu always; Desktop unless `-NoDesktopShortcut`.
- **No launch.** Add `-NoLaunch` when testing.
- **Uninstall.** A shortcut is created that runs the generated
  `uninstall.ps1`; it removes shortcuts, the PATH entry, and (unless
  `-KeepData`) your progress.

## Notes for maintainers

- PyInstaller is only needed at build time; people who install Bolo never see
  it.
- The AI features expect [Ollama](https://ollama.com) and a model such as
  `llama3.2:3b`. The installer does not download models, because they are
  large and the rest of Bolo works without them. The apps say this in plain
  words when Ollama is missing.
- SmartScreen may warn about an unsigned `.exe`. Signing needs a code-signing
  certificate; without one, tell people to choose *More info → Run anyway*.
  The zip's contents are inspectable and the source is in this repository.
- The zip is roughly 40–60 MB, mostly three self-contained Python runtimes.
