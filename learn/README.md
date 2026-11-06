# Learn Bolo — for people who have never programmed

No experience needed. If you can read, type, and follow a recipe, you can do this.

> Prefer a window to a terminal? Double-click **`BOLO - Learn Bolo.bat`** in the
> project folder. The app has 18 lessons, an editor, Run and Check buttons, an
> App Studio for building real desktop windows, a local tutor, a playground, and
> a searchable reference. These files are the same course in reading form.

---

## What is a program?

A program is a **list of instructions** for a computer. The computer is fast and
patient but completely literal — it does exactly what the words say, in order,
and nothing more.

You write the instructions in a *language*. Bolo is one. It is small on
purpose: a few dozen words, and everything is read left to right.

## How to run a lesson

Open a terminal in this folder and type:

```bat
bolo learn\01_say.bolo
```

That's it. Each lesson is a text file you can open in Notepad or VS Code. Change
something, run it again, see what happens. **Breaking things is the fastest way
to learn**, so break them.

If you prefer to experiment one line at a time, type `bolo` with no file name.
You will get a prompt:

```text
Bolo 1.0 - type code, press Enter. Type help or quit.
bolo> say("hello")
hello
bolo> 2 + 3
5
bolo> quit
```

---

## The lessons, in order

| Lesson | File | The one idea |
|-------:|------|--------------|
| 1 | `01_say.bolo` | Making the computer talk |
| 2 | `02_numbers.bolo` | Numbers and text are different things |
| 3 | `03_boxes.bolo` | Giving a value a name (variables) |
| 4 | `04_choices.bolo` | Doing something only when a condition is true |
| 5 | `05_lists.bolo` | Many values in one place, and the word `then` |
| 6 | `06_repeat.bolo` | Doing the same thing to every item |
| 7 | `07_recipes.bolo` | Teaching the computer a new trick |
| 8 | `08_real_job.bolo` | A real chore: files on your disk |
| 9 | `09_keep.bolo` | Values that must not change, and `give` |
| 10 | `10_loop.bolo` | `loop N times`, `stop`, and `next` |
| 11 | `11_handy_tools.bolo` | `numbered`, `empty`, `clamp`, `between` |

Work through them in order. Each takes about five minutes. Every lesson ends
with a **Try it** section — do those, they are where the learning happens.

## Words you will meet

| Bolo | In plain English |
|---|---|
| `say(...)` | print something on the screen |
| `"hello"` | text (always inside quotes) |
| `42`, `3.14` | numbers (no quotes) |
| `x = 5` | put the value 5 into a box named `x` |
| `keep x = 5` | put a value in a box that must not change |
| `true` / `false` | yes / no |
| `nothing` | "no value at all" |
| `if ... { } otherwise { }` | if this is true, do that; otherwise do the other thing (`else` also works) |
| `is`, `is not` | same as `==` and `!=`, but reads like English |
| `for x in list { }` | do this once for each item |
| `loop 3 times { }` | do this a set number of times |
| `while ... { }` | keep doing this while something stays true |
| `stop` / `next` | leave the loop now / skip to the next step (`break`/`continue` also work) |
| `try ... catch` | try something, and do this instead if it fails |
| `table(...)` | a labelled box with many shelves: values kept under names |
| `{name}` inside text | put a value into a sentence |
| `use "file.bolo"` | run another file and keep its tricks |
| `to name(...) { }` | teach the computer a new trick |
| `give` / `return` | hand an answer back and stop the recipe |
| `\|>` | "then": pass the left side into the right side |
| `{ it * 2 }` | a small unnamed trick; `it` is whatever you hand it |
| `#` | the rest of the line is a note for humans |

## If you see an error

Errors are help, not punishment. Bolo tries to explain them in normal words and
points at the spot:

```text
bolo: learn\demo.bolo: line 3
  3 | say("I am " + 12)
    |              ^
  you can't add text and a number
  hint: you can add two numbers, two pieces of text, or two lists
```

Read the bottom line first. It usually tells you exactly what to change. Common
ones:

| Message | What it means |
|---|---|
| `I don't know the name 'nmae'` | a typo, or you used a box before putting something in it |
| `you can't add text and a number` | wrap the number: `text(12)` |
| `this '{' is never closed` | add a `}` |
| `expected ')' but found the end of the line` | a bracket is missing |

## After the lessons

- **`learn/challenges/README.md`** — six real jobs with no hand-holding: a word
  report, a duplicate cleaner, a log scanner, a file sorter, a backup tool. Sample
  data is included. This is where the lessons turn into skill.
- **Make a window.** A Bolo program can be a real desktop app:

  ```bolo
  win = window("Hello", 460, 300)
  heading(win, "Hello!")
  button(win, "Close", { close(win) })
  show(win)
  ```

  Run `bolo examples\hello_app.bolo` to try one, or open **App Studio** in the
  learning app. `examples\notes_app.bolo` opens and saves text files, and
  `examples\tasks_app.bolo` is a complete to-do app that saves itself.
- **Ask the tutor.** The learning app's Tutor page uses a local Ollama model.
  It can explain an error, give a hint, or check your code. Nothing is sent to
  the internet.
- **Write code with AI.** Double-click `BOLO - Chat With AI.bat` for a separate
  app with a chat and an editor. Ask about anything, or switch to *Bolo code*
  mode and ask for a program. Press *Use code from answer*, then *Check* or
  *Run*. It can also explain or fix the code you wrote.
- Read `examples/hello.bolo` — it is the whole language in one page.
- Read `examples/tidy.bolo` — a genuinely useful script. Run it on a folder of
  junk; it only *prints* a plan unless you add `--go`.
- Open `README.md` for the full reference when you want to know what else exists.

You do not need to memorise anything. Even experienced programmers look things up
constantly — that is most of the job.
