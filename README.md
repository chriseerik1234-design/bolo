# Bolo

**Bolo** (say it *BOH-loh*) is a small programming language for everyday
file, text, and desktop-app chores. It is meant to be readable by someone who
has never programmed, and useful to someone who has.

```bolo
files("photos") |> filter({ ext(it) is "jpg" }) |> each({ say(name(it)) })
```

That shows every JPEG in `photos`. In Python it is eight lines and two imports; in
bash it is a `find -exec` you have to look up every time.

Bolo is built from scratch in one file — lexer, parser, interpreter — about
2,800 lines of plain Python with no dependencies.

---

## Install it on any Windows PC

On a machine without Python, one PowerShell command installs Bolo for the
current user (no administrator rights):

```powershell
irm https://github.com/chriseerik1234-design/bolo/releases/latest/download/install.ps1 | iex
```

It downloads the release zip, puts the programs in
`%LOCALAPPDATA%\Programs\Bolo`, and adds Start Menu shortcuts for **Bolo Learn**
and **Bolo Chat**. Uninstall any time from Start Menu → Bolo → Uninstall Bolo.

Prefer the files? Download
[Bolo-Windows.zip](https://github.com/chriseerik1234-design/bolo/releases/latest/download/Bolo-Windows.zip)
and unzip it anywhere. The source lives at
[github.com/chriseerik1234-design/bolo](https://github.com/chriseerik1234-design/bolo),
and the friendly download page is
[chriseerik1234-design.github.io/bolo](https://chriseerik1234-design.github.io/bolo/).

---

## The learning app

Double-click **`BOLO - Learn Bolo.bat`**. No terminal, nothing to install.

It is a small desktop app built around the language:

- **15 lessons**, from `say("hello")` to recursion, closures, regex, real
  files, and a finished desktop app. Each one explains a piece of Bolo, gives
  you a task, and checks your answer. It says exactly what is still missing,
  and *Show answer* is there when you want to see a working solution.
- **An editor** with syntax colours, Run and Check buttons, and `F5` to run.
- **App Studio**, where you write a program and open it as a real desktop
  window. Six ready templates: Hello, Greeter, Tip calculator, Notes, To-do
  list, Clock.
- **A playground** with one live session, so variables survive between runs.
- **A tutor** running locally through Ollama. It knows Bolo, can see the
  lesson and your code, and never sends anything to the internet.
- **A reference** covering every builtin and every piece of syntax, searchable.
- **Automatic saving** of your progress and your code in `bolo_progress.json`.

Lessons run inside `app_sandbox/`, which the app clears before each run, so
`write`, `move` and `delete` cannot reach your real documents. App Studio runs
each app in its own process, so a window never freezes the editor.

The app is `bolo_app.py`: plain Tkinter from the Python standard library, and
it imports `bolo.py` directly. Desktop windows live in `bolo_gui.py`; the
local-AI client is `bolo_ai.py`. Nothing else to install.

## Bolo Chat — the separate AI app

Double-click **`BOLO - Chat With AI.bat`**. This is a standalone window for
talking with the local model, separate from the lessons:

- **A real chatbot.** Ask about anything — a recipe, an idea, a word, the news
  you paste in — not just code. Bolo is its specialty, not its only subject.
- **Two modes.** *Chat* is warm and general. *Bolo code* switches to a precise
  coding prompt that returns one complete program. Both use the same window.
- **Chat on the left, code on the right.** Ask for a program, or press
  *Explain my code*, *Fix my code*, *Improve my code*.
- **Use code from answer** moves the last code block out of the chat and into
  the editor, ready to check or run.
- **Check** parses the code and points at the problem line without running it.
- **Run** executes the editor in `coder_sandbox/` and shows the output. Window
  programs open normally; *Stop* closes them.
- **Open** and **Save** work with ordinary `.bolo` files.
- It uses the dedicated `bolo-chat` model and sends nothing to the internet.

The app is `bolo_chat.py`. It shares `bolo_ai.py` with the learning app's
tutor page.

## Start here if you have never programmed

If you prefer reading over app windows: go to **[`learn/README.md`](learn/README.md)**
and work through the eight lessons in order. They assume nothing: not what a
variable is, not what a file extension is, not that brackets must balance.
Each lesson is a small file you run and edit.

```
learn/01_say.bolo        making the computer talk
learn/02_numbers.bolo    numbers and text are different things
learn/03_boxes.bolo      giving a value a name
learn/04_choices.bolo    if ... else
learn/05_lists.bolo      lists, and the word "then"
learn/06_repeat.bolo     doing something for every item
learn/07_recipes.bolo    functions
learn/08_real_job.bolo   a real chore with real files
```

Then **[`learn/challenges/README.md`](learn/challenges/README.md)** has six real
jobs — no hand-holding, sample data included. That's the step from "I followed a
lesson" to "I built a tool".

## Running Bolo from a terminal

```bat
bolo learn\01_say.bolo               a file
bolo -e "2 + 3 |> say"              one line
bolo                                type code live (a prompt)
```

The prompt is the quickest place to experiment. It shows the answer to every
line you type:

```text
bolo> 2 + 3
5
bolo> [3, 1, 2] |> sort
[1, 2, 3]
```

`bolo.cmd` finds Python for you. You can also call the interpreter directly:
`python bolo.py learn\01_say.bolo`.

One quoting quirk: in PowerShell, `-e` with text inside needs the inner quotes
escaped, or PowerShell eats them:

```powershell
.\bolo.cmd -e 'say(\"hi\")'
```

## A taste

```bolo
# Names and lists
folder = "photos"
photos = files(folder) |> filter({ ext(it) is "jpg" })

say("found " + text(length(photos)) + " photos")

# Your own trick (a function)
to bucket(extension) {
  if ["jpg", "png"] |> contains(extension) { return "images" }
  "other"
}

# Repeating, and real file work
for photo in photos {
  mkdir(path(folder, "images"))
  move(photo, path(folder, "images", name(photo)))
}
```

## The language

### Values

| Value | Looks like | Notes |
|---|---|---|
| text | `"hello"`, `'hi'` | either quote style; `\n` is a new line |
| number | `42`, `3.14`, `-7` | whole numbers and decimals are the same type |
| boolean | `true`, `false` | answers to questions |
| nothing | `nothing` or `nil` | "no value at all" |
| list | `[1, 2, 3]` | ordered, counted from 0 |
| table | `table("name", "Mari")` | values kept under names, like a labelled box |
| function | `say`, `{ it * 2 }`, `to f() {}` | something you can call |

Common builtins exist under two names: the friendly one first, then the short one.

| Friendly | Also works |
|---|---|
| `say` | `print` |
| `length` | `count` |
| `text` | `str` |
| `number` | `num` |
| `average` | `mean` |
| `nothing` | `nil` |

Both spellings are identical; use whichever reads better.

### Notes (comments)

`#` starts a comment that runs to the end of the line.

### Operators, loosest to tightest

| Precedence | Operators | Notes |
|---:|---|---|
| 1 | `or` | returns the winning value |
| 2 | `and` | short-circuits |
| 3 | `== != < <= > >=` | also written `is`, `is not`; plus `in`, `not in` |
| 4 | `\|>` | pipeline (feeds the first argument) |
| 5 | `+ -` | `+` also joins text and lists |
| 6 | `* / %` | `%` is the remainder |
| 7 | `-x`, `not x` | unary |

Because `|>` sits above comparisons, `xs |> length > 0` means
`(xs |> length) > 0`. Because it sits below arithmetic, `1 + 2 |> say` means
`(1 + 2) |> say`.

### Pipelines

`value |> f(a, b)` is exactly `f(value, a, b)`. Every builtin is written
subject-first for this reason. Chains read top to bottom and may span lines:

```bolo
files("in")
  |> filter({ ext(it) is "txt" })
  |> map({ name(it) })
  |> sort
```

### Small recipes (lambdas)

`{ it * 2 }` is a one-value function where the value is named `it`. Name the
values when you need more, or when a name reads better:

```bolo
[1, 2, 3, 4] |> reduce(0, { total, n -> total + n })   # 10
```

A lambda body may hold several statements; its last value is returned.
Assignments inside a lambda stay local to it.

### Functions

```bolo
to greet(who, greeting) {
  greeting + ", " + who + "!"
}

greet("maailm", "Tere")     # "Tere, maailm!"
```

The last expression is the return value, or use `return value` to leave early.
Functions are closures and may call themselves.

### Choices

`if` is an expression, so it produces a value:

```bolo
label = if n is 1 { "one" } else if n is 2 { "two" } else { "many" }
```

A block's value is the value of its last statement. An `if` with no `else`
produces `nothing` when the condition is false.

### Loops

```bolo
for file in files(".") {
  say(name(file))
}
```

`for` walks lists, text (character by character), and tables (each item is a
`[key, value]` list). `range(1, 4)` gives `[1, 2, 3]`.

When you do not know how many times you need to repeat, use `while`:

```bolo
n = 3
while n > 0 {
  say(n)
  n = n - 1
}
```

Something inside the loop must change the question, or it runs forever. Bolo
stops a runaway loop after five million steps and says so.

`break` leaves the nearest loop immediately. `continue` skips the rest of the
body and starts the next step:

```bolo
for n in [1, 2, 3, 4] {
  if n is 2 { continue }
  if n is 4 { break }
  say(n)          # 1, then 3
}
```

### Tables

A table keeps values under names. It is the friendly version of a dictionary:

```bolo
person = table("name", "Mari", "age", 12)
person["city"] = "Tartu"
put(person, "job", "student")

say(person["name"])           # Mari
say(get(person, "job"))       # student
say(get(person, "pet", "-"))  # - (no error when the key is missing)
say(has(person, "age"))       # true
```

Walk a table with `pairs`. Each item is a `[key, value]` list, so a two-name
`for` is the natural shape:

```bolo
for key, value in pairs(person) {
  say("{key} = {value}")
}
```

`keys(t)` and `values(t)` return ordinary lists. `remove(t, key)` takes an entry
out. `length(t)` counts the entries.

### Text with values inside

Put an expression in `{ }` inside text and its value appears there:

```bolo
name = "Mari"
age = 12
say("Hello, {name}! Next year you are {age + 1}.")
# Hello, Mari! Next year you are 13.
```

Write `{{` and `}}` for real braces. If what is inside is not a value — pasted
JSON, a note, an unbalanced bracket — Bolo leaves the braces as ordinary text,
so JSON can be written without escaping.

A backslash only means something in front of `n`, `t`, `r`, `"`, `'` or another
backslash. Every other backslash stays exactly as typed, so a regex like
`test(name, "\d+")` and a path like `read("C:\Users\Cli\Desktop\list.csv")`
work without doubling. A folder whose name starts with `n`, `t` or `r` still
needs `\\` there (`C:\notes`), or write it with forward slashes: `C:/Users/Cli`.

### Problems you can catch

`fail("message")` stops with a problem of your own. `try` catches it (and any
ordinary Bolo error) so the program can carry on:

```bolo
try {
  delete("important.txt")
} catch problem {
  say("I could not do that: " + problem)
}
```

The name after `catch` holds the error text; `catch { }` without a name works
too. `test`, `fail` and the file builtins all become friendly when wrapped this
way.

### Sharing code between files

`use "tools.bolo"` runs another file once, right there. The functions and names
it creates stay available in the file that used it:

```bolo
use "tools.bolo"
say(greet("Mari"))
```

A bare name gets `.bolo` added: `use tools` is `use "tools.bolo"`. Files are
found next to the program that uses them.

### Membership

`in` asks whether a value is inside a list, some text, or a table's keys:

```bolo
if "jpg" in ["jpg", "png"] { say("a picture") }
if "cat" in "concatenate" { say("yes") }
if not has(person, "age") { say("age unknown") }
```

### Positions

```bolo
xs = [10, 20, 30]
xs[0]      # 10
xs[-1]     # 30
"abc"[1]   # "b"
```

Counting starts at 0. Negative positions count from the end.

## Builtins

All builtins take their subject first, so they compose with `|>`.

**Output**

| | |
|---|---|
| `say(a, b, ...)` | write values, space separated |

**Conversion**

| | |
|---|---|
| `text(x)` / `str(x)` | to text: `text(12)` → `"12"` |
| `number(x)` / `num(x)` | parse text, keep numbers |
| `int(x)` | truncate or parse to a whole number |
| `bool(x)` | truthiness: `0`, `""`, `[]`, `false`, `nothing` are false |
| `type(x)` | `"text"`, `"number"`, `"boolean"`, `"nothing"`, `"list"`, `"table"`, `"function"`, `"window"`, `"widget"` |

**Text**

| | |
|---|---|
| `upper(s)`, `lower(s)`, `trim(s)` | |
| `split(s, sep?)` | whitespace when no separator |
| `words(s)`, `lines(s)` | |
| `replace(s, from, to)` | plain text, not regex |
| `starts(s, p)`, `ends(s, p)`, `contains(s, p)` | |
| `test(s, regex)` | `true` when the pattern matches |
| `find(s, regex)` | every match as a list |
| `pad(s, width)` | add spaces on the right |
| `repeat(x, times)` | copy text or a list several times |

**Lists**

| | |
|---|---|
| `length(x)` / `count(x)` | length of a list, text, or table |
| `first(xs)`, `last(xs)` | `nothing` when empty |
| `take(xs, n)`, `skip(xs, n)` | |
| `sort(xs)`, `sortby(xs, fn)`, `reverse(xs)`, `unique(xs)` | |
| `sum(xs)`, `join(xs, glue?)` | |
| `push(xs, x)` | returns a new list |
| `map(xs, fn)`, `filter(xs, fn)`, `each(xs, fn)` | `each` returns the list |
| `reduce(xs, start, fn)` | |
| `range(n)` / `range(a, b)` | `range(3)` is `[0, 1, 2]` |
| `index_of(xs, x)` | position, or `-1` when missing |
| `insert(xs, i, x)` | a copy with one item added |
| `flatten(xs)`, `slice(xs, from, to?)` | |

**Tables**

| | |
|---|---|
| `table(...)` | empty, or from key, value pairs |
| `put(t, key, value)` | store or replace; `t[key] = value` works too |
| `get(t, key, fallback?)` | safe read with a fallback |
| `has(t, key)`, `remove(t, key)` | |
| `keys(t)`, `values(t)`, `pairs(t)` | lists of names, values, `[key, value]` |

**Numbers, time and chance**

| | |
|---|---|
| `round(n, places?)`, `floor(n)`, `ceil(n)` | |
| `abs(n)`, `sqrt(n)` | |
| `min(xs)`, `max(xs)`, `average(xs)` / `mean(xs)` | |
| `random()`, `random_int(a, b)`, `choose(xs)` | |
| `now()`, `today()` | date and time as text |
| `sleep(seconds)` | wait, then carry on |

**JSON**

| | |
|---|---|
| `json(text)` | read JSON into tables, lists, numbers and text |
| `to_json(x)` | turn lists and tables into JSON text |

**Files and paths**

| | |
|---|---|
| `files(folder?, pattern?)` | files directly inside, sorted |
| `walk(folder?, pattern?)` | recursive |
| `read(p)`, `write(p, text)`, `append(p, text)` | UTF-8; parents auto-created |
| `move(p, to)`, `copy(p, to)`, `delete(p)`, `mkdir(p)` | |
| `exists(p)`, `isfile(p)`, `isdir(p)` | | |
| `size(p)` | bytes in a file |
| `modified(p)` | when it last changed, as sortable text |
| `name(p)`, `stem(p)`, `ext(p)`, `parent(p)` | `ext` has no dot: `"jpg"` |
| `path(a, b, ...)` | join path parts safely |

**Asking and stopping**

| | |
|---|---|
| `prompt(text?)` | ask the person at the keyboard for a line |
| `fail(text)` | stop with a problem `try`/`catch` can catch |
| `quit(code?)` | end the program; `0` means success |

**Desktop apps**

These are imported only when a program uses them (`bolo_gui.py`).

| | |
|---|---|
| `window(title?, width?, height?)` | make a window; one per program |
| `row(parent)` | a horizontal strip for side-by-side widgets |
| `label(parent, text)`, `heading(parent, text)` | text, or a big title |
| `button(parent, text, action?)` | clickable; `it` is the button inside the recipe |
| `input(parent)`, `textbox(parent, lines?)` | one-line field, or a large box |
| `check(parent, text)` | tick box; `value` is `true` or `false` |
| `value(w)`, `set(w, x)` | read or change what a widget holds |
| `on_click(w, fn)`, `on_change(w, fn)` | attach an action to a click or a change |
| `add_line(box, text)`, `clear(w)` | append a line, or empty a widget |
| `show(win)` | open the window and keep it open |
| `alert(msg, title?)`, `ask(msg, title?)` | message box, or yes/no question |
| `choose_file(title?)`, `save_file(title?)` | pick a file to open or save |
| `later(win, ms, fn)`, `every(win, ms, fn)` | run once after a delay, or repeatedly |
| `close(win)` | close the window |

## Build a desktop app

The last line of an app is nearly always `show(win)`. Without it, the window
is made but never appears (Bolo reminds you).

```bolo
win = window("Greeter", 480, 340)
heading(win, "Say hello")
label(win, "What is your name?")

name = input(win)
message = label(win, "")

button(win, "Greet", {
  set(message, "Hello, " + value(name) + "!")
})

show(win)
```

Widgets stack from top to bottom. Put widgets inside a `row(win)` to place them
side by side. `value(...)` reads an input, textbox or tick box; `set(...)`
changes a label, input, textbox, or tick box.

Ready to run:

```bat
bolo examples\hello_app.bolo
bolo examples\notes_app.bolo
bolo examples\tasks_app.bolo
```

### A complete app in one Bolo file

`examples\tasks_app.bolo` is a working to-do list: add tasks, tick them off,
delete by number, clear finished ones, and it saves itself to `tasks.json`.
Double-click **`BOLO - Tasks.bat`** to try it.

What makes it a real program, in about 170 lines of Bolo:

- a **table** for the words and another for the done marks
- a **number** kept in `state["next"]` so ids never repeat
- **functions** for the screen (`refresh`), the buttons (`add_task`,
  `mark_done`, `delete_task`) and the file (`save_tasks`, `load_tasks`)
- `try` / `catch` around saving, so a read-only folder shows a message
  instead of crashing
- `json` and `to_json` for the saved list
- `ask(...)` before clearing finished tasks

None of it is a special case in the engine; every line uses the same builtins
the lessons teach.

## The local tutor

The learning app's **Tutor** page talks to a model running on your own machine
through [Ollama](https://ollama.com). Nothing is sent to the internet.

The source for Bolo's models is in `ollama/`. To rebuild them:

```bat
ollama create bolo-tutor -f ollama\Bolo-Tutor.Modelfile
ollama create bolo-chat -f ollama\Bolo-Chat.Modelfile
ollama create bolo-coder -f ollama\Bolo-Coder.Modelfile
```

The learning app checks for `bolo-tutor:latest` first; Bolo Chat checks for
`bolo-chat:latest` in Chat mode and `bolo-coder:latest` in code mode. Both then
fall back to common small models such as `llama3.2:3b`. If Ollama is not
running, each app says so in plain words. The first answer can take half a
minute while the model loads.

## The `args` variable

`args` is a list of the words after the script name:

```bat
bolo tidy.bolo C:\Downloads --go
```

```bolo
folder = args |> first
if folder is nothing { folder = "." }
go = args |> contains("--go")
```

## Example: `examples/tidy.bolo`

Sorts one folder into `images/`, `text/`, `docs/`, `audio/`, `archives/`,
`other/`. Dry run by default:

```bat
bolo examples\tidy.bolo C:\Users\Kasutaja\Downloads
bolo examples\tidy.bolo C:\Users\Kasutaja\Downloads --go
```

## Errors are meant to be read

Bolo points at the exact character and says what went wrong in plain words:

```text
bolo: demo.bolo: line 3
  3 | say("I am " + 12)
    |              ^
  you can't add text and a number
  hint: you can add two numbers, two pieces of text, or two lists
```

Misspelled names get a suggestion ("did you mean 'print'?"), and common
mistakes like adding text to a number or miscounting positions get a hint that
names the fix.

## How it works

```
source text
   │  tokenize()      characters → tokens (numbers, text, names, operators)
   ▼
tokens
   │  Parser          recursive descent + precedence climbing → AST
   ▼
AST (dataclasses: Num, Call, Binary, If, ...)
   │  Interp          tree-walking evaluation with lexical Envs
   ▼
values (Python int/float/str/bool/None/list — the language has no other runtime)
```

Three details worth knowing:

1. **Newlines are tokens.** They end statements, but the parser skips them when
   the next line continues an expression (`|>`, `is`, `and`, ...), which is why
   leading-pipe pipelines work.
2. **`|>` is desugared during parsing** into an ordinary call. The interpreter
   has no idea pipelines exist.
3. **Errors carry a line and a column**, so the CLI can draw a caret under the
   exact mistake.

The learning app, `bolo_app.py`, is a thin Tkinter layer over the same
interpreter. It keeps the course, the reference, and the playground in ordinary
Python data, then calls `bolo.parse` and `Interp.run` to execute code. No second
language implementation, and no behaviour that differs from the command line.

## Tests

```bat
python -m unittest discover -s tests -v
```

174 tests: arithmetic, parsing rules, closures, recursion, pipelines, regex
helpers, `while` and `break`, `try`/`catch`, tables, text interpolation, `use`,
JSON, beginner wording, error messages, real file operations in a temporary
folder, desktop windows, and Bolo Chat's answer handling. The app's share checks
that every lesson solution still passes its own Check, every starter still fails
it, every builtin appears in the reference, every reference example parses, and
every playground snippet runs.

## Known limits (on purpose, for now)

- No imports, packages, or classes. Use `use "file.bolo"` to share code.
- Numbers are Python ints and floats; no decimals for money, no big integers.
- One table type; keys are text or numbers, not lists or tables.
- `delete` on a folder removes it recursively — read scripts before running them.
- Windows have a simple vertical stack, rows, and the controls listed above: no
  menus, tabs, canvases, or drag-and-drop yet.
- Tree-walking, so roughly 50× slower than Python. Fine for chores.

Natural next steps: a package folder for `use`, more window controls, an
Estonian translation of the lessons, and signed executables so Windows does not
warn about the installer.

## License

Bolo is released under the [MIT License](LICENSE). In plain words: use it,
change it, share it, even in something you sell — just keep the copyright
notice, and understand that it comes with no warranty.

The name "Bolo" and the project are not trademarked; if you publish a changed
version, say clearly that it is yours, so people are not confused about where
it came from.
