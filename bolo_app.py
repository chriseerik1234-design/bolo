"""Bolo Learn - a small desktop app that teaches Bolo from zero.

Start it by double-clicking "BOLO - Learn Bolo.bat", the installed Bolo
shortcut, or with:

    pythonw bolo_app.py

What is inside:

  * 15 short lessons. Each one has an explanation, a task, an editor,
    and a Check button that tells you whether you actually did it.
  * A playground with one live session, so variables survive between runs.
  * A reference covering every builtin and every piece of syntax.
  * Progress saved to bolo_progress.json, including your own code.

The lessons run inside app_sandbox/, a folder this app resets before each
run. File lessons cannot damage anything outside it.
"""

from __future__ import annotations

import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk

if getattr(sys, "frozen", False):
    # A packaged Bolo.exe: code comes from the bundle, but progress and the
    # practice folder belong beside the installed program, not in a temp dir.
    APP_DIR = Path(sys.executable).resolve().parent
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", APP_DIR)) / "Bolo"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    APP_DIR = Path(__file__).resolve().parent
    DATA_DIR = APP_DIR
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo  # noqa: E402  (import after the path fix above)
import bolo_ai  # noqa: E402

SANDBOX = DATA_DIR / "app_sandbox"
PROGRESS_FILE = DATA_DIR / "bolo_progress.json"

# ---------------------------------------------------------------------------
# Look
# ---------------------------------------------------------------------------

PAPER = "#f6f5f1"
PANEL = "#ffffff"
SIDEBAR = "#eae7df"
SIDEBAR_SOFT = "#f1efe9"
INK = "#1d2227"
MUTED = "#6d7178"
RULE = "#d8d4ca"
ACCENT = "#2f6b4f"
ACCENT_DARK = "#234f3b"
ACCENT_SOFT = "#e2efe7"
WARN_SOFT = "#fdf1d7"
CONSOLE_BG = "#1c2126"
CONSOLE_FG = "#e8e6e0"
CONSOLE_MUTED = "#9aa1a9"
ERR = "#ff9d8c"
OK = "#9bd9a9"
HIGHLIGHT = "#fff2c4"

# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


@dataclass
class Lesson:
    id: str
    title: str
    subtitle: str
    body: str
    task: str
    starter: str
    must: list[str] = field(default_factory=list)
    solution: str = ""
    sandbox: bool = False
    gui: bool = False
    code_must: list[str] = field(default_factory=list)


LESSONS: list[Lesson] = [
    Lesson(
        id="1",
        title="Make it talk",
        subtitle="say, and why quotes matter",
        body="""## A program is a list of instructions

The computer reads them top to bottom and does exactly what they say.

`say(...)` writes something on the screen. Text lives inside quotes:

    say("Hello!")

Numbers do not need quotes:

    say(42)

## Why the quotes matter

Quotes mean "print these exact words". Without them, Bolo looks for a box
with that name instead. The error will tell you so - and that is useful,
not a disaster. Errors are how the language explains its rules.

## One more thing

A line starting with `#` is a note for humans. Bolo skips it completely.

    # this line does nothing""",
        task='Add a second say(...) line that prints exactly:  Bolo is running.',
        starter='say("Hello, world!")\n\n# Add your second line below this note.\n',
        must=["Hello, world!", "Bolo is running."],
        solution='say("Hello, world!")\nsay("Bolo is running.")\n',
    ),
    Lesson(
        id="2",
        title="Numbers and text",
        subtitle="two kinds of value that do not mix",
        body="""## Numbers

    say(2 + 3)      # 5
    say(10 - 4)     # 6
    say(6 * 7)      # 42
    say(10 / 4)     # 2.5
    say(10 % 3)     # 1   the remainder

## Text

Text is inside quotes. `+` joins two pieces of text:

    say("bread" + " and " + "cheese")

## They do not mix

`"12"` is text. `12` is a number. Adding them is an error, on purpose:
the result would be ambiguous. Convert first.

    say("I am " + text(12) + " years old")
    say(1 + number("41"))        # 42

`text()` turns anything into text. `number()` reads text as a number.""",
        task='Print exactly:  17 % 5 = 2   (build it with text(), not by typing 2).',
        starter="""say(2 + 3)
say(10 % 3)

say("2 + 3 = " + text(2 + 3))

# Your turn: print  17 % 5 = 2
""",
        must=["2 + 3 = 5", "17 % 5 = 2"],
        solution="""say(2 + 3)
say(10 % 3)

say("2 + 3 = " + text(2 + 3))
say("17 % 5 = " + text(17 % 5))
""",
    ),
    Lesson(
        id="3",
        title="Boxes with names",
        subtitle="variables remember a value",
        body="""## A box with a name

    name = "Mari"
    age = 12

The `=` means "put this value in this box". It is not a question.

    say(name + " is " + text(age))

A name is yours to choose. No spaces, no quotes around it. Capital letters
matter: `Age` and `age` are two different boxes.

## The box can change

    age = age + 1

The right side is worked out first, then the result goes back in the box.
So `age` becomes 13.

## Why boxes exist

Without them you would retype the same value everywhere, and a change
would mean finding every copy.""",
        task='After adding one year, print exactly:  Mari is 13',
        starter="""name = "Mari"
age = 12

say(name)
say(age)

# Add one year to age, then print:  Mari is 13
""",
        must=["Mari is 13"],
        solution="""name = "Mari"
age = 12

say(name)
say(age)

age = age + 1
say(name + " is " + text(age))
""",
    ),
    Lesson(
        id="4",
        title="Choosing",
        subtitle="if, else, and questions",
        body="""## Asking a yes/no question

    if age < 18 {
      say("young")
    } else {
      say("grown up")
    }

The lines between `{` and `}` run only when the question is true.

## Text needs `is`

    if weather is "rain" {
      say("take an umbrella")
    }

`is` asks whether two things are equal. `is not` asks the opposite.
Use them for text: `=` stores a value, so it cannot ask a question.

## Several choices

    if score > 90 {
      say("excellent")
    } else if score > 70 {
      say("good")
    } else {
      say("keep practising")
    }

The first true question wins; the rest are skipped.

## Comparisons

`is`  `is not`  `<`  `>`  `<=`  `>=`""",
        task='Change weather to "rain" and print "umbrella" only when it is raining.',
        starter="""score = 85

if score > 90 {
  say("excellent")
} else if score > 70 {
  say("good")
} else {
  say("keep practising")
}

weather = "sun"

# Your turn: set weather to "rain", then add an if that prints "umbrella".
""",
        must=["good", "umbrella"],
        solution="""score = 85

if score > 90 {
  say("excellent")
} else if score > 70 {
  say("good")
} else {
  say("keep practising")
}

weather = "rain"

if weather is "rain" {
  say("umbrella")
}
""",
    ),
    Lesson(
        id="5",
        title="Lists",
        subtitle="many values in one place",
        body="""## A row of values

    fruits = ["apple", "pear", "plum"]

Positions start at 0. That surprises everybody once, and then never again.

    say(fruits[0])        # apple
    say(fruits[-1])       # plum   negative counts from the end

Out of range is a helpful error, not a crash:

    say(fruits[5])        # there is no position 5

## Handy words

    length(fruits)        # 3
    first(fruits)         # apple
    last(fruits)          # plum
    take(fruits, 2)       # the first two
    skip(fruits, 1)       # everything after the first
    contains(fruits, "pear")

Text behaves like a list of characters for all of these.""",
        task="Print exactly three lines:  count: 3   then   first: apple   then   last: plum",
        starter="""fruits = ["apple", "pear", "plum"]

say(fruits[0])
say(fruits[-1])

# Your turn: print three labelled lines:
# count: 3
# first: apple
# last: plum
""",
        must=["count: 3", "first: apple", "last: plum"],
        solution="""fruits = ["apple", "pear", "plum"]

say("count: " + text(length(fruits)))
say("first: " + first(fruits))
say("last: " + last(fruits))
""",
    ),
    Lesson(
        id="6",
        title="Pipelines",
        subtitle='the word "then"',
        body="""## Pass the value on

`|>` takes the value on its left and hands it to the thing on its right:

    [3, 1, 2] |> sort

is exactly the same as:

    sort([3, 1, 2])

The value becomes the first argument. That is the entire trick, and it is
why every Bolo builtin takes the thing it works on first.

## It reads like a sentence

    files("photos")
      |> filter({ ext(it) is "jpg" })
      |> each({ say(name(it)) })

Each line hands its result to the next. A whole job fits on four lines.

## It can be short

    [3, 1, 4, 1, 5] |> unique |> sort |> sum      # 13""",
        task="From `numbers`, print the unique values sorted and joined by dashes:  1-3-4-5",
        starter="""numbers = [3, 1, 4, 1, 5]

say(numbers |> unique |> sort |> sum)

# Your turn: print 1-3-4-5 using unique, sort and join.
""",
        must=["13", "1-3-4-5"],
        solution="""numbers = [3, 1, 4, 1, 5]

say(numbers |> unique |> sort |> sum)
say(numbers |> unique |> sort |> join("-"))
""",
    ),
    Lesson(
        id="7",
        title="Small recipes",
        subtitle="lambdas: { it ... }",
        body="""## A recipe you do not need to name

    { it * 2 }

`it` is the value handed in. This tiny function is called a *lambda*.

## The four workers

    map(xs, fn)        change every item
    filter(xs, fn)     keep items where fn says true
    each(xs, fn)       do something with every item
    reduce(xs, start, fn)   fold the whole list into one value

    [1, 2, 3] |> map({ it * 10 })          # [10, 20, 30]
    [1, 2, 3] |> filter({ it > 1 })        # [2, 3]
    [1, 2, 3] |> reduce(0, { a, b -> a + b })   # 6

## More than one value

Name them when one letter is not enough:

    { a, b -> a + b }""",
        task="Keep the even numbers, multiply each by 10, and print the list:  [20, 40, 60]",
        starter="""numbers = [1, 2, 3, 4, 5, 6]

say(numbers |> filter({ it % 2 is 0 }))

# Your turn: even numbers, each times 10, in one pipeline.
""",
        must=["[2, 4, 6]", "[20, 40, 60]"],
        solution="""numbers = [1, 2, 3, 4, 5, 6]

say(numbers |> filter({ it % 2 is 0 }))
say(numbers |> filter({ it % 2 is 0 }) |> map({ it * 10 }))
""",
    ),
    Lesson(
        id="8",
        title="Loops",
        subtitle="for, range, and building a result",
        body="""## Do it again for each item

    for fruit in ["apple", "pear"] {
      say(fruit)
    }

The box (`fruit`) exists only inside the loop, so names cannot leak out.

## Counting

`range(1, 11)` gives 1 to 10. It stops before the second number, the same
rule as list positions.

    total = 0
    for n in range(1, 11) {
      total = total + n
    }
    say(total)          # 55

`total = total + n` is the standard way to build up an answer: start with
a box, add to it, look at it at the end.

## Loops or pipelines?

If the answer is "make a new list", a pipeline is shorter. If you need to
keep a running total or print as you go, a loop is clearer.""",
        task="Print the squares 1 to 100, separated by spaces:  1 4 9 16 25 36 49 64 81 100",
        starter="""total = 0
for n in range(1, 11) {
  total = total + n
}
say(total)

# Your turn: build a list of squares, then join with spaces.
""",
        must=["55", "1 4 9 16 25 36 49 64 81 100"],
        solution="""total = 0
for n in range(1, 11) {
  total = total + n
}
say(total)

squares = []
for n in range(1, 11) {
  squares = push(squares, n * n)
}
say(squares |> join(" "))
""",
    ),
    Lesson(
        id="9",
        title="Your own tricks",
        subtitle="functions with to ... { }",
        body="""## Teach Bolo a new trick

    to greet(who) {
      "Hello, " + who + "!"
    }

    say(greet("Mari"))      # Hello, Mari!

The last line of the body is the answer. The names in `( )` are the values
it needs. Call it with `greet("Mari")`.

## Leaving early

    to describe(age) {
      if age < 18 { return "young" }
      "grown up"
    }

`return` stops the trick right there with that answer. Without it, the
last line is the answer.

## Why bother

A trick gives a name to a job. Use it twice and you have already saved
yourself a copy-paste mistake.""",
        task="Write to add(a, b) and print add(2, 3) so the output includes exactly:  5",
        starter="""to greet(who) {
  "Hello, " + who + "!"
}

say(greet("Mari"))

# Your turn: write to add(a, b), then print add(2, 3).
""",
        must=["Hello, Mari!", "5"],
        solution="""to greet(who) {
  "Hello, " + who + "!"
}

say(greet("Mari"))

to add(a, b) {
  a + b
}

say(add(2, 3))
""",
    ),
    Lesson(
        id="10",
        title="Recursion and closures",
        subtitle="a trick that calls itself, and tricks that remember",
        body="""## A trick that calls itself

    to fact(n) {
      if n <= 1 { return 1 }
      n * fact(n - 1)
    }

Every call must get closer to a stopping point, or it never ends. That
stopping point is the `if` line. Miss it and Bolo will tell you the
trick went round too many times.

## Tricks that remember values

A function can hand back another function:

    to adder(n) {
      { it + n }
    }

    add5 = adder(5)
    say(add5(2))        # 7

The inner recipe still remembers `n` after `adder` has finished. This is
called a *closure*, and it is how small configurable tools are built.""",
        task="Print 120 (factorial of 5) and 7 (a closure that adds 5).",
        starter="""to fact(n) {
  if n <= 1 { return 1 }
  n * fact(n - 1)
}

say(fact(5))

# Your turn: write to adder(n) that returns { it + n }.
# Then add5 = adder(5) and print add5(2).
""",
        must=["120", "7"],
        solution="""to fact(n) {
  if n <= 1 { return 1 }
  n * fact(n - 1)
}

say(fact(5))

to adder(n) {
  { it + n }
}

add5 = adder(5)
say(add5(2))
""",
    ),
    Lesson(
        id="11",
        title="The text toolbox",
        subtitle="every word for working with words",
        body="""## Clean, cut, search

    trim(s)                  cut spaces from both ends
    upper(s) / lower(s)      change case
    split(s, sep?)           text -> list
    words(s) / lines(s)      split on spaces / on line breaks
    replace(s, from, to)     plain text, not patterns
    starts(s, x) / ends(s, x)
    contains(s, x)           is x somewhere inside?
    test(s, pattern)         regular expression -> true / false
    find(s, pattern)         regular expression -> list of matches

## Patterns, briefly

`find("abc123def456", "[0-9]+")` gives `["123", "456"]`.
`[0-9]+` means "one or more digits". Useful pieces:

    [0-9]     a digit
    [a-z]     a lowercase letter
    +         one or more
    *         zero or more
    ^  $      start and end of the text

## Text is a list of characters

Positions, `length`, `take`, `skip` and `reverse` all work on text too.""",
        task='Print "bat", print "true" (from starts), and print the digits in abc123def456 joined by commas.',
        starter="""say(trim("  Hello World  ") |> upper)
say(words("the cat sat on the mat") |> length)
say("a,b,c" |> split(",") |> join(" + "))

# Your turn: replace, starts, and find the digits.
# replace("cat", "c", "b")        -> bat
# starts("hello", "he")           -> true
# "abc123def456" |> find("[0-9]+") |> join(",")
""",
        must=["HELLO WORLD", "6", "a + b + c", "bat", "true", "123,456"],
        solution="""say(trim("  Hello World  ") |> upper)
say(words("the cat sat on the mat") |> length)
say("a,b,c" |> split(",") |> join(" + "))

say(replace("cat", "c", "b"))
say(starts("hello", "he"))
say("abc123def456" |> find("[0-9]+") |> join(","))
""",
    ),
    Lesson(
        id="12",
        title="The list toolbox",
        subtitle="sort, unique, sum, join and friends",
        body="""## Order and shape

    sort(xs)              smallest / alphabetical first
    sortby(xs, key)       order by a recipe
    reverse(xs)           backwards (works on text too)
    unique(xs)            one of each, in first-seen order
    sum(xs)               add up the numbers
    join(xs, glue?)       list -> text
    push(xs, x)           a NEW list with x on the end

## Edges

    take(xs, n) / skip(xs, n)
    first(xs) / last(xs)      nothing when the list is empty
    contains(xs, x)

## Nothing is changed in place

`sort`, `push`, `reverse` and the rest return a **new** list. The old one
is untouched. That sounds like a detail now, and later it saves you from
a whole family of confusing bugs.

    xs = [3, 1]
    ys = xs |> sort        # xs is still [3, 1]""",
        task='Print the words sorted by length, the first two joined with ", ", and "hello" backwards.',
        starter="""words = ["pear", "fig", "banana", "kiwi"]

say([3, 1, 2] |> sort)
say([1, 2, 2, 3] |> unique)
say([1, 2, 3, 4] |> sum)

# Your turn: sortby + take + join, then reverse.
""",
        must=["[1, 2, 3]", "[1, 2, 3]", "10", "fig, pear", "olleh"],
        solution="""words = ["pear", "fig", "banana", "kiwi"]

say([3, 1, 2] |> sort)
say([1, 2, 2, 3] |> unique)
say([1, 2, 3, 4] |> sum)

say(words |> sortby({ length(it) }) |> take(2) |> join(", "))
say("hello" |> reverse)
""",
    ),
    Lesson(
        id="13",
        title="Real files",
        subtitle="reading, writing, and paths",
        body="""## Real files, safely

This lesson runs inside `app_sandbox/`, a folder the app clears each time
you press Run. Nothing outside it is touched, so you cannot break your
own documents by experimenting here.

    write(path("work", "note.txt"), "hello")
    say(read(path("work", "note.txt")))

`write` creates missing folders for you. `path(...)` joins pieces with the
right slash, so you never build paths by hand.

## Looking around

    files("work")          files directly inside, sorted
    walk(".")              everything below, recursively
    name(p)                "note.txt"
    stem(p)                "note"
    ext(p)                 "txt"      (no dot)
    parent(p)              the folder above
    exists(p) / isfile(p) / isdir(p)

## Changing things

    mkdir(p)               make a folder (fine if it exists)
    move(from, to)         move or rename
    copy(from, to)         duplicate
    append(p, text)        add to the end of a file
    delete(p)              remove a file, or a folder and its contents

Read a script before running it. `delete` is real.""",
        task="Print exactly:  text files: 1   and   photo extension: jpg",
        starter="""mkdir("work")
write(path("work", "shopping.txt"), "milk\\nbread\\ncheese")
write(path("work", "photo.jpg"), "not really a photo")

say(files("work") |> length)
say(read(path("work", "shopping.txt")) |> lines |> length)

# Your turn:
# count the .txt files                -> text files: 1
# print the extension of photo.jpg    -> photo extension: jpg
""",
        must=["text files: 1", "photo extension: jpg"],
        solution="""mkdir("work")
write(path("work", "shopping.txt"), "milk\\nbread\\ncheese")
write(path("work", "photo.jpg"), "not really a photo")

say(files("work") |> length)
say(read(path("work", "shopping.txt")) |> lines |> length)

say("text files: " + text(files("work") |> filter({ ext(it) is "txt" }) |> length))
say("photo extension: " + ext(path("work", "photo.jpg")))
""",
        sandbox=True,
    ),
    Lesson(
        id="14",
        title="Types and errors",
        subtitle="what a value is, and how to read a problem",
        body="""## Types, in one table

    type(42)         "number"
    type("hi")       "text"
    type([])         "list"
    type(true)       "boolean"
    type(nothing)    "nothing"

`nothing` (also spelled `nil`) means "no value at all". `first([])` and
`last([])` give it, and a function with no answer gives it.

## Truthiness

Some values count as false without being `false`:

    bool(0)          false
    bool("")         false
    bool([])         false
    bool(nothing)    false
    bool("x")        true

This is why `if first(items) { ... }` is a safe check.

## Errors are instructions

Read the bottom line first, then the caret. It names the fix.

    bolo: your code: line 3
      3 | say("age: " + 12)
        |              ^
      you can't add text and a number
      hint: you can add two numbers, two pieces of text, or two lists

Misspelled names get "did you mean ...?", a missing `}` says which `{` was
never closed, and using `=` in an `if` tells you to use `is`.

## Other conversions

`int(3.9)` gives 3. `number("41")` gives 41. `text(41)` gives "41".""",
        task='Print four labelled lines: 0 is false, empty text is false, empty list is false, any text is true.',
        starter="""say(type(42))
say(type("hi"))
say(type([]))
say(type(nothing))

# Your turn: four labelled lines, using bool():
# 0 is false
# empty text is false
# empty list is false
# any text is true
""",
        must=[
            "0 is false",
            "empty text is false",
            "empty list is false",
            "any text is true",
        ],
        solution="""say(type(42))
say(type("hi"))
say(type([]))
say(type(nothing))

say("0 is " + text(bool(0)))
say("empty text is " + text(bool("")))
say("empty list is " + text(bool([])))
say("any text is " + text(bool("x")))
""",
    ),
    Lesson(
        id="15",
        title="Build an app",
        subtitle="windows, buttons, and events",
        body="""## A real window

    win = window("My first app", 460, 320)
    heading(win, "Hello!")
    label(win, "This is a desktop app, made with Bolo.")
    button(win, "Close", { close(win) })
    show(win)

`window(...)` makes the window. Everything you add goes inside it, from
top to bottom. `show(win)` opens it and keeps it open until it is closed.

Press **Run** on this lesson: the app opens in its own window. Close that
window and the lesson is waiting for you again.

## Asking for a value

    name = input(win)
    message = label(win, "")

    button(win, "Greet", {
      set(message, "Hello, " + value(name) + "!")
    })

`value(widget)` reads what is inside. `set(widget, ...)` changes it.
The recipe in `{ }` runs when the button is clicked. If you need the
widget itself inside the recipe, it is called `it`.

## Rows and other controls

    bar = row(win)
    button(bar, "Save", { alert("Saved") })
    button(bar, "Quit", { close(win) })

    notes = textbox(win, 8)      a big box; add_line and value
    agree = check(win, "Done")   value is true or false
    file = choose_file()         a path, or nothing
    ask("Delete it?")            true or false

Widgets inside a `row` sit side by side. Everything else stacks down.

## The rule to remember

An app without `show(win)` never appears. Bolo will remind you if you
forget. The last line of an app is nearly always `show(win)`.""",
        task=(
            "Build a greeter: a window, a heading, an input, a button that "
            "changes a label with set(), and show(win)."
        ),
        starter="""win = window("Greeter", 480, 340)
heading(win, "Say hello")
label(win, "What is your name?")

# Your turn:
# name = input(win)
# message = label(win, "")
# button(win, "Greet", { ... set(message, ...) ... })
# show(win)
""",
        must=[],
        solution="""win = window("Greeter", 480, 340)
heading(win, "Say hello")
label(win, "What is your name?")

name = input(win)
message = label(win, "")

button(win, "Greet", {
  set(message, "Hello, " + value(name) + "!")
})

show(win)
""",
        gui=True,
        code_must=["window(", "heading(", "input(", "button(", "set(", "value(", "show("],
    ),
]


# ---------------------------------------------------------------------------
# Reference - every word in the language
# ---------------------------------------------------------------------------

REFERENCE: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Syntax",
        [
            (
                "comments",
                "A note for humans. Everything after # on that line is ignored.",
                '# say("this never runs")',
            ),
            (
                "values",
                "Six kinds: text, number, boolean, nothing, list, function. That is the whole type system.",
                '# the six kinds of value\n"hello"      # text\n42           # number\ntrue         # boolean\nnothing      # nothing\n[1, 2, 3]    # list\n{ it * 2 }   # function',
            ),
            (
                "variables",
                "`=` puts a value in a named box. Names are case-sensitive and have no spaces or quotes.",
                'score = 10\nscore = score + 1\nsay(score)      # 11',
            ),
            (
                "operators",
                "Loosest to tightest: or | and | is is-not < <= > >= | pipeline | + - | * / % | -x not x",
                "1 + 2 * 3        # 7, not 9\nxs |> length > 0 # (xs |> length) > 0",
            ),
            (
                "pipeline  |>",
                "Hands the left value in as the FIRST argument on the right. value |> f(a) is f(value, a). Chains may span lines.",
                'files("photos")\n  |> filter({ ext(it) is "jpg" })\n  |> each({ say(name(it)) })',
            ),
            (
                "lambda  { it ... }",
                "A small unnamed function. `it` is the value handed in. Name the values with { a, b -> ... } when you need more than one.",
                "[1, 2, 3] |> map({ it * 2 })          # [2, 4, 6]\n[1, 2, 3] |> reduce(0, { a, b -> a + b })   # 6",
            ),
            (
                "function  to name(...) { }",
                "Teach Bolo a trick. The last line of the body is the answer; `return` leaves early. Functions can call themselves.",
                "to greet(who) {\n  \"Hello, \" + who + \"!\"\n}\nsay(greet(\"Mari\"))",
            ),
            (
                "if / else",
                "Ask a yes/no question and run a block when it is true. if is an expression, so it can produce a value.",
                'if age < 18 { say("young") } else { say("grown up") }\n\nlabel = if n is 1 { "one" } else { "many" }',
            ),
            (
                "for",
                "Run a block once for each item. The loop box exists only inside the loop.",
                "for fruit in [\"apple\", \"pear\"] {\n  say(fruit)\n}",
            ),
            (
                "positions  xs[i]",
                "Counting starts at 0. Negative positions count from the end. Works on lists and text.",
                'xs = [10, 20, 30]\nxs[0]     # 10\nxs[-1]    # 30\n"abc"[1]  # "b"',
            ),
            (
                "text escapes",
                "Inside text, \\n is a new line, \\\" is a quote, and \\\\ is a backslash.",
                'say("one\\ntwo")\nsay("she said \\"hi\\"")',
            ),
            (
                "text with values  {..}",
                "Put an expression inside { } in text and its value appears there. Write {{ and }} for real braces. If what is inside is not a value (JSON, for example), the braces stay as ordinary text.",
                'name = "Mari"\nsay("Hello, {name}!")\nsay("{2 + 3} apples")',
            ),
            (
                "while",
                "Repeat while the question stays true. Change something inside the loop, or it never stops.",
                'n = 3\nwhile n > 0 {\n  say(n)\n  n = n - 1\n}',
            ),
            (
                "break / continue",
                "break leaves the loop now. continue jumps to the next step and skips the rest of the body.",
                'for n in [1, 2, 3, 4] {\n  if n is 2 { continue }\n  if n is 4 { break }\n  say(n)\n}',
            ),
            (
                "try / catch",
                "Run a block. If it fails, run the catch block instead. The name holds the error message. Raise your own with fail(text).",
                'try {\n  fail("the file is missing")\n} catch problem {\n  say("I could not do it: " + problem)\n}',
            ),
            (
                "in  /  not in",
                "Ask whether a value is inside a list, some text, or a table's keys.",
                'if "jpg" in ["jpg", "png"] { say("a picture") }\nif "cat" in "concatenate" { say("yes") }',
            ),
            (
                "table  {key: value}",
                "A table keeps values under names. Read and write with t[key]. length(t) counts the entries.",
                'person = table("name", "Mari")\nperson["age"] = 12\nput(person, "city", "Tartu")\nsay(person["name"], person["age"])',
            ),
            (
                "use",
                "Run another .bolo file beside this one, once. Its functions and boxes stay available. Good for splitting a big program into small files.",
                'use "tools.bolo"\nuse helpers\nsay(greet("Mari"))',
            ),
        ],
    ),
    (
        "Output",
        [
            (
                "say(value, ...)   also: print",
                "Write values on the screen, separated by spaces. The beginner name is say; print does the same thing.",
                'say("hello", 42)      # hello 42',
            ),
        ],
    ),
    (
        "Values and conversion",
        [
            (
                "text(x)   also: str",
                "Turn any value into text. Needed when joining a number to text.",
                'say("age: " + text(12))',
            ),
            (
                "number(x)   also: num",
                "Read text as a number. Whole numbers and decimals both work.",
                'number("41") + 1       # 42',
            ),
            (
                "int(x)",
                "Cut a decimal down to a whole number, or read text as one.",
                "int(3.9)               # 3",
            ),
            (
                "bool(x)",
                "Is this value considered true? 0, \"\", [], false and nothing are false; everything else is true.",
                'bool("")               # false',
            ),
            (
                "type(x)",
                "The kind of value, as text: number, text, boolean, nothing, list, function.",
                "type([1, 2])           # list",
            ),
            (
                "nothing   also: nil",
                'The value meaning "no value at all".',
                "say(nothing)           # nothing\nfirst([])              # nothing",
            ),
            (
                "args",
                "A list of the words typed after the script name, when running a .bolo file from the terminal.",
                "folder = args |> first\nif folder is nothing { folder = \".\" }",
            ),
        ],
    ),
    (
        "Text",
        [
            ("upper(s)", "All capitals.", 'upper("abc")            # ABC'),
            ("lower(s)", "All lowercase.", 'lower("ABC")            # abc'),
            (
                "trim(s)",
                "Remove spaces and tabs from both ends.",
                'trim("  hi  ")         # "hi"',
            ),
            (
                "split(s, sep?)",
                "Cut text into a list. Without a separator it splits on any whitespace.",
                'split("a,b", ",")       # ["a", "b"]',
            ),
            (
                "words(s)",
                "Split on whitespace and drop the empty pieces. The usual way to count words.",
                'words("the cat") |> length   # 2',
            ),
            (
                "lines(s)",
                "Split into lines on \\n. The usual way to walk a file.",
                'lines("a\\nb")          # ["a", "b"]',
            ),
            (
                "replace(s, from, to)",
                "Plain text replacement, not a pattern. Every occurrence.",
                'replace("cat", "c", "b")      # bat',
            ),
            (
                "starts(s, x)",
                "True when s begins with x.",
                'starts("hello", "he")  # true',
            ),
            ("ends(s, x)", "True when s finishes with x.", 'ends("hello", "lo")    # true'),
            (
                "contains(s, x)",
                "True when x is inside s. On a list, true when the list holds x.",
                'contains("hello", "ell")     # true\n[1, 2] |> contains(2)        # true',
            ),
            (
                "test(s, pattern)",
                "Does the regular expression match anywhere in s?",
                'test("abc123", "[0-9]")      # true',
            ),
            (
                "find(s, pattern)",
                "Every regular expression match, as a list.",
                'find("a1b22", "[0-9]+")      # ["1", "22"]',
            ),
            (
                "pad(s, width)",
                "Add spaces on the right until the text is wide enough. Handy for lining up columns.",
                'say(pad("name", 10) + "age")',
            ),
            (
                "repeat(x, times)",
                "Copy text or a list several times.",
                'repeat("-", 10)        # ----------\nrepeat([1, 2], 2)      # [1, 2, 1, 2]',
            ),
        ],
    ),
    (
        "Lists",
        [
            (
                "length(x)   also: count",
                "How many items in a list, or characters in text.",
                'length([1, 2, 3])      # 3\nlength("hello")        # 5',
            ),
            ("first(xs) / last(xs)", "The first or last item. nothing when empty.", "first([5, 6])          # 5"),
            ("take(xs, n) / skip(xs, n)", "The first n items, or everything after the first n. Work on text too.", 'take([1,2,3], 2)       # [1, 2]'),
            ("sort(xs)", "Smallest first, or alphabetical for text.", 'sort([3, 1, 2])        # [1, 2, 3]'),
            (
                "sortby(xs, key)",
                "Order by whatever the key recipe returns. Stable: ties keep their old order.",
                'words |> sortby({ length(it) })',
            ),
            ("reverse(xs)", "Backwards. Works on text and lists.", 'reverse([1, 2, 3])     # [3, 2, 1]'),
            (
                "unique(xs)",
                "One of each value, in the order first seen.",
                "unique([1, 2, 1])      # [1, 2]",
            ),
            ("sum(xs)", "Add up a list of numbers.", "sum([1, 2, 3])         # 6"),
            (
                "join(xs, glue?)",
                "Turn a list into text. Glue is empty unless you give one.",
                'join(["a", "b"], "-")  # a-b',
            ),
            (
                "push(xs, x)",
                "A NEW list with x on the end. The old list is unchanged.",
                "push([1], 2)           # [1, 2]",
            ),
            (
                "map(xs, fn)",
                "Change every item with the recipe.",
                "[1, 2] |> map({ it * 10 })      # [10, 20]",
            ),
            (
                "filter(xs, fn)",
                "Keep only the items where the recipe returns a true value.",
                "[1, 2, 3] |> filter({ it > 1 }) # [2, 3]",
            ),
            (
                "each(xs, fn)",
                "Do something with every item, usually say. Returns the list.",
                '["a", "b"] |> each({ say(it) })',
            ),
            (
                "reduce(xs, start, fn)",
                "Fold the list into one value. fn receives (so-far, next).",
                "[1, 2, 3] |> reduce(0, { a, b -> a + b })   # 6",
            ),
            (
                "range(n) / range(a, b)",
                "A list of numbers. range(3) is [0, 1, 2]; range(1, 4) is [1, 2, 3]. It stops before the last number.",
                "for n in range(1, 4) { say(n) }",
            ),
            (
                "index_of(xs, x)",
                "Where an item sits, or -1 when it is not there. Works on text too.",
                'index_of(["a", "b"], "b")   # 1\nindex_of("hello", "ll")     # 2',
            ),
            (
                "insert(xs, i, x)",
                "A copy with x added at position i. The old list is unchanged.",
                'insert([1, 3], 1, 2)        # [1, 2, 3]',
            ),
            (
                "flatten(xs)",
                "One list holding the items of the lists inside.",
                "flatten([[1], [2, 3]])      # [1, 2, 3]",
            ),
            (
                "slice(xs, from, to?)",
                "Part of a list or text. Counting starts at 0; the end position is not included.",
                'slice([10, 20, 30, 40], 1, 3)   # [20, 30]\nslice("hello", 0, 4)           # hell',
            ),
        ],
    ),
    (
        "Files and paths",
        [
            (
                "files(folder?, pattern?)",
                "Files directly inside a folder, sorted. The pattern matches names, e.g. \"*.txt\". Defaults to the current folder.",
                'files("photos")        # full paths\nfiles("photos", "*.jpg")',
            ),
            (
                "walk(folder?, pattern?)",
                "Like files, but searches every folder below, recursively.",
                'walk(".") |> filter({ ext(it) is "bolo" })',
            ),
            (
                "read(path)",
                "The whole file as text. UTF-8.",
                'say(read("notes.txt"))',
            ),
            (
                "write(path, text)",
                "Replace a file with text, creating folders if needed.",
                'write("out/report.txt", "done")',
            ),
            (
                "append(path, text)",
                "Add text to the end of a file, creating it if needed.",
                'append("log.txt", "one more line\\n")',
            ),
            (
                "mkdir(path)",
                "Make a folder, including missing parents. Fine if it already exists.",
                'mkdir("sorted/images")',
            ),
            ("move(from, to) / copy(from, to)", "Move (or rename) and duplicate. The destination folder is created.", 'move("a.jpg", "images/a.jpg")'),
            (
                "delete(path)",
                "Remove a file, or a folder and everything inside it. There is no undo.",
                'delete("temp")',
            ),
            ("exists(p) / isfile(p) / isdir(p)", "Ask what is there before you act.", 'if isfile(p) { say("found it") }'),
            (
                "name(p) / stem(p) / ext(p) / parent(p)",
                "Pieces of a path. ext has no dot.",
                'name("cat.jpg")        # cat.jpg\nstem("cat.jpg")        # cat\next("cat.jpg")         # jpg\nparent("a/b.txt")      # a',
            ),
            (
                "path(a, b, ...)",
                "Join path pieces with the right separator for this machine.",
                'path("photos", "cat.jpg")',
            ),
            (
                "json(text)",
                "Read JSON text into tables, lists, numbers and text.",
                'data = json("{\\"name\\": \\"Mari\\"}")\nsay(data["name"])',
            ),
            (
                "to_json(x)",
                "Turn lists and tables into JSON text, ready to write to a file.",
                'say(to_json(table("name", "Mari")))',
            ),
        ],
    ),
    (
        "Tables",
        [
            (
                "table(...)",
                "An empty table, or one built from key, value pairs. A table keeps values under names, like a labelled box with many shelves.",
                'person = table("name", "Mari", "age", 12)\nempty = table()',
            ),
            (
                "put(t, key, value)",
                "Store a value under a key, replacing what was there. t[key] = value does the same.",
                'put(person, "city", "Tartu")',
            ),
            (
                "get(t, key, fallback?)",
                "Read one value. When the key is missing you get the fallback (nothing by default) instead of an error.",
                'get(person, "age")        # 12\nget(person, "job", "none") # none',
            ),
            (
                "has(t, key)",
                "Is this key in the table?",
                'if has(person, "age") { say("known") }',
            ),
            (
                "remove(t, key)",
                "Take one key out, if it is there. Returns the same table.",
                'remove(person, "age")',
            ),
            (
                "keys(t) / values(t)",
                "All the names, or all the values, as a list.",
                'keys(person)      # ["name", "age"]\nvalues(person)    # ["Mari", 12]',
            ),
            (
                "pairs(t)",
                "One [key, value] list per entry. Use it to walk a table.",
                'for key, value in pairs(person) {\n  say(key, "=", value)\n}',
            ),
        ],
    ),
    (
        "Numbers, time and chance",
        [
            ("round(n, places?)", "The nearest whole number, or nearest 0.1 / 0.01 with places.", 'round(2.6)        # 3\nround(2.456, 2)   # 2.46'),
            ("floor(n) / ceil(n)", "The whole number below, or above.", 'floor(2.9)        # 2\nceil(2.1)         # 3'),
            ("abs(n) / sqrt(n)", "Distance from zero, and square root.", 'abs(-4)           # 4\nsqrt(9)           # 3'),
            ("min(xs) / max(xs)", "The smallest or largest. Give a list, or several values.", 'min([3, 1, 2])    # 1\nmax(3, 9, 2)      # 9'),
            ("average(xs)   also: mean", "The sum divided by the count.", 'average([2, 4, 6]) # 4'),
            ("random()", "A decimal from 0 up to (not including) 1.", 'chance = random()   # 0.731...'),
            ("random_int(a, b)", "A whole number from a to b, both ends allowed.", 'dice = random_int(1, 6)'),
            ("choose(xs)", "Pick one item at random.", 'say(choose(["rock", "paper", "scissors"]))'),
            ("now() / today()", "The date and time here, as text.", 'say(now())    # 2026-11-05 14:03:22\nsay(today())  # 2026-11-05'),
            ("sleep(seconds)", "Wait, then carry on. Whole and decimal seconds both work.", 'sleep(0.5)'),
        ],
    ),
    (
        "Asking and stopping",
        [
            (
                "prompt(text?)",
                "Ask the person at the keyboard for a line of text, in a terminal program.",
                'name = prompt("Your name?")\nsay("Hello, " + name)',
            ),
            (
                "fail(text)",
                "Stop with a problem of your own. try/catch can catch it.",
                'if not isfile("notes.txt") {\n  fail("notes.txt is missing")\n}',
            ),
            (
                "quit(code?)",
                "End the program now. 0 means it worked; anything else is a problem.",
                'if args is [] { quit(1) }',
            ),
        ],
    ),
    (
        "Desktop apps",
        [
            (
                "window(title?, width?, height?)",
                "Make a real desktop window. Add things to it, then show(win). One window per program.",
                'win = window("My app", 460, 320)\nheading(win, "Hello")\nshow(win)',
            ),
            (
                "label(parent, text) / heading(parent, text)",
                "A line of text, or a big title. Widgets stack from top to bottom inside a window.",
                'label(win, "Ready when you are.")\nheading(win, "My notes")',
            ),
            (
                "row(parent)",
                "A horizontal strip. Put labels and buttons inside it to place them side by side.",
                'bar = row(win)\nbutton(bar, "Save", { save_it() })\nbutton(bar, "Quit", { close(win) })',
            ),
            (
                "button(parent, text, action?)",
                "A clickable button. The action runs when it is clicked; `it` is the button itself.",
                'button(win, "Greet", { alert("Hello!") })',
            ),
            (
                "input(parent) / textbox(parent, lines?)",
                "A one-line field, or a bigger box for several lines. Read them with value.",
                'name = input(win)\nnotes = textbox(win, 8)',
            ),
            (
                "check(parent, text)",
                "A tick box. value(check) is true or false.",
                'agree = check(win, "I agree")\nif value(agree) { alert("Thanks") }',
            ),
            (
                "value(widget) / set(widget, value)",
                "Read or change what a widget holds. Works for labels, inputs, textboxes, checks and buttons.",
                'say(value(name))\nset(message, "Hello, " + value(name))',
            ),
            (
                "on_click(widget, action)",
                "Attach another action to a button or tick box. on_change fires when an input or textbox changes.",
                'on_click(go, { set(result, "clicked") })\non_change(name, { set(result, value(name)) })',
            ),
            (
                "add_line(textbox, text) / clear(widget)",
                "Append a line to a textbox, or empty any widget.",
                'add_line(log, "started")\nclear(log)',
            ),
            (
                "show(win)",
                "Open the window and keep it open until it is closed. The last line of an app is nearly always show(win).",
                'show(win)',
            ),
            (
                "alert(message, title?) / ask(message, title?)",
                "A small message box, or a yes/no question that returns true or false.",
                'alert("Saved")\nif ask("Delete it?") { delete(file) }',
            ),
            (
                "choose_file(title?) / save_file(title?)",
                "Let the learner pick a file to read, or a place to save. Returns nothing when cancelled.",
                'file = choose_file()\nif file is not nothing { say(read(file)) }',
            ),
            (
                "later(win, ms, action) / every(win, ms, action)",
                "Run an action once after a delay, or again and again. Milliseconds: 1000 is one second.",
                'every(win, 1000, { set(clock, "tick") })',
            ),
            (
                "close(win)",
                "Close the window. Also works on any widget inside it.",
                'button(win, "Quit", { close(win) })',
            ),
        ],
    ),
]

PLAYGROUND_SNIPPETS: list[tuple[str, str]] = [
    (
        "A pipeline",
        "[3, 1, 4, 1, 5]\n  |> unique\n  |> sort\n  |> join(\"-\")\n  |> say\n",
    ),
    (
        "Text clean-up",
        'say("  Hello, World  " |> trim |> lower |> replace(",", ""))\nsay(words("one two three") |> length)\n',
    ),
    (
        "List work",
        'numbers = [1, 2, 3, 4, 5, 6]\nsay(numbers |> filter({ it % 2 is 0 }) |> map({ it * it }))\n',
    ),
    (
        "A function",
        'to shout(text) {\n  upper(text) + "!"\n}\n\nsay(shout("hello"))\n',
    ),
    (
        "A loop",
        "total = 0\nfor n in range(1, 11) {\n  total = total + n\n}\nsay(total)\n",
    ),
    (
        "Files",
        'mkdir("play")\nwrite(path("play", "note.txt"), "hello\\nfrom bolo")\nsay(read(path("play", "note.txt")))\nsay(files("play") |> length)\n',
    ),
]

# Ready-made windows for the App Studio. Each one is a complete program.
APP_TEMPLATES: list[tuple[str, str]] = [
    (
        "Hello window",
        'win = window("Hello from Bolo", 460, 300)\n'
        'heading(win, "Hello!")\n'
        'label(win, "This window is a real desktop app.")\n'
        'button(win, "Close", { close(win) })\n'
        'show(win)\n',
    ),
    (
        "Greeter",
        'win = window("Greeter", 480, 340)\n'
        'heading(win, "Say hello")\n'
        'label(win, "What is your name?")\n'
        'name = input(win)\n'
        'message = label(win, "")\n'
        'button(win, "Greet", {\n'
        '  set(message, "Hello, " + value(name) + "!")\n'
        '})\n'
        'show(win)\n',
    ),
    (
        "Tip calculator",
        'win = window("Tip calculator", 460, 390)\n'
        'heading(win, "Tip calculator")\n'
        'label(win, "Bill amount")\n'
        'bill = input(win)\n'
        'label(win, "Tip percent")\n'
        'percent = input(win)\n'
        'answer = label(win, "")\n'
        'button(win, "Calculate", {\n'
        '  total = number(value(bill))\n'
        '  tip = number(value(percent))\n'
        '  extra = total * tip / 100\n'
        '  set(answer, "Tip: " + text(extra) + "    Total: " + text(total + extra))\n'
        '})\n'
        'show(win)\n',
    ),
    (
        "Notes",
        'win = window("Notes", 580, 470)\n'
        'heading(win, "Notes")\n'
        'note = textbox(win, 12)\n'
        'bar = row(win)\n'
        'button(bar, "Open", {\n'
        '  file = choose_file()\n'
        '  if file is not nothing { set(note, read(file)) }\n'
        '})\n'
        'button(bar, "Save", {\n'
        '  file = save_file()\n'
        '  if file is not nothing {\n'
        '    write(file, value(note))\n'
        '    alert("Saved")\n'
        '  }\n'
        '})\n'
        'button(bar, "Quit", { close(win) })\n'
        'show(win)\n',
    ),
    (
        "To-do list",
        'win = window("To-do list", 520, 470)\n'
        'heading(win, "My tasks")\n'
        'items = table()\n'
        'counter = table("next", 1)\n'
        '\n'
        'to show_tasks() {\n'
        '  out = ""\n'
        '  for id in sort(keys(items)) {\n'
        '    out = out + text(id) + ". " + items[id] + "\\n"\n'
        '  }\n'
        '  if out is "" { out = "Nothing yet. Add one below." }\n'
        '  out\n'
        '}\n'
        '\n'
        'entry = input(win)\n'
        'bar = row(win)\n'
        'board = textbox(win, 10)\n'
        'button(bar, "Add", {\n'
        '  words = trim(value(entry))\n'
        '  if words is "" {\n'
        '    alert("Type a task first.")\n'
        '  } else {\n'
        '    id = counter["next"]\n'
        '    items[id] = words\n'
        '    counter["next"] = id + 1\n'
        '    set(entry, "")\n'
        '    set(board, show_tasks())\n'
        '  }\n'
        '})\n'
        'button(bar, "Quit", { close(win) })\n'
        'show(win)\n',
    ),
    (
        "Clock",
        'win = window("Clock", 420, 280)\n'
        'heading(win, "Tick")\n'
        'face = label(win, "0")\n'
        'every(win, 1000, {\n'
        '  set(face, text(number(value(face)) + 1))\n'
        '})\n'
        'show(win)\n',
    ),
]


# ---------------------------------------------------------------------------
# Running code
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    output: str
    error: str | None = None
    value: object = None
    error_line: int | None = None


def reset_sandbox() -> None:
    shutil.rmtree(SANDBOX, ignore_errors=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)


RECURSION_HELP = (
    "bolo: this went round too many times\n"
    "  A function that calls itself needs a stopping point.\n"
    "  Look for the 'if' that should end it, and check it can actually be reached."
)


def run_source(
    source: str,
    interp: bolo.Interp | None = None,
    reset_first: bool = True,
) -> RunResult:
    """Run Bolo code inside the sandbox and collect its output.

    The app never runs learner code in the project folder: the working
    directory is app_sandbox/, so write/move/delete cannot reach anything
    the learner cares about.
    """
    reset_sandbox() if reset_first else SANDBOX.mkdir(parents=True, exist_ok=True)

    buffer = io.StringIO()
    error: str | None = None
    error_line: int | None = None
    value = None

    previous_cwd = os.getcwd()
    previous_stdout = sys.stdout
    os.chdir(SANDBOX)
    sys.stdout = buffer
    try:
        runner = interp if interp is not None else bolo.Interp()
        try:
            value = runner.run(bolo.parse(source))
        except bolo.BoloError as err:
            error = bolo.format_error(source, "your code", err)
            error_line = err.line
        except RecursionError:
            error = RECURSION_HELP
        except Exception as exc:  # noqa: BLE001 - a learner should see something useful
            error = f"bolo: unexpected problem: {exc}"
    finally:
        sys.stdout = previous_stdout
        os.chdir(previous_cwd)

    return RunResult(buffer.getvalue(), error, value, error_line)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class BoloApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bolo - learn by doing")
        self.geometry("1280x840")
        self.minsize(1000, 680)
        self.configure(bg=PAPER)

        self.lessons = LESSONS
        self.current = 0
        self.view = "lesson"
        self.progress: dict = self._load_progress()
        self.play_interp = bolo.Interp()
        self._highlight_job: str | None = None
        self._error_tag_owner: tk.Text | None = None

        self._app_proc = None
        self._app_log: Path | None = None
        self._app_origin = "apps"
        self._app_poll_job: str | None = None
        self.last_error: str | None = None

        self.tutor_model: str | None = None
        self.tutor_history: list[dict] = []
        self.tutor_pending = False
        self.tutor_queue: queue.Queue = queue.Queue()
        self.tutor_checked = False
        self._tutor_context = "lesson"

        self._setup_fonts()
        self._setup_styles()
        self._build()
        self._poll_tutor_queue()

        saved_index = self.progress.get("last_lesson")
        if isinstance(saved_index, int) and 0 <= saved_index < len(self.lessons):
            self.current = saved_index

        self._select_lesson(self.current)
        self._refresh_sidebar()
        self._refresh_progress()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- setup --------------------------------------------------------------
    def _setup_fonts(self) -> None:
        self.f_h1 = tkfont.Font(family="Segoe UI Semibold", size=20)
        self.f_h2 = tkfont.Font(family="Segoe UI Semibold", size=12)
        self.f_ui = tkfont.Font(family="Segoe UI", size=10)
        self.f_ui_bold = tkfont.Font(family="Segoe UI Semibold", size=10)
        self.f_small = tkfont.Font(family="Segoe UI", size=9)
        self.f_code = tkfont.Font(family="Consolas", size=11)
        self.f_code_small = tkfont.Font(family="Consolas", size=9)

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=PAPER, foreground=INK, font=self.f_ui)
        style.configure("TFrame", background=PAPER)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("Side.TFrame", background=SIDEBAR)

        style.configure(
            "TButton",
            background="#e7e4dc",
            foreground=INK,
            borderwidth=0,
            focusthickness=0,
            padding=(12, 7),
            font=self.f_ui,
        )
        style.map(
            "TButton",
            background=[("active", "#dcd8ce"), ("pressed", "#d2cec4")],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#ffffff",
            bordercolor=ACCENT,
            padding=(14, 7),
            font=self.f_ui_bold,
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
            foreground=[("disabled", "#dfe9e3")],
        )
        style.configure(
            "Ghost.TButton",
            background=PANEL,
            foreground=MUTED,
            padding=(10, 6),
        )
        style.map("Ghost.TButton", background=[("active", SIDEBAR_SOFT)])
        style.configure(
            "Nav.TButton",
            background=SIDEBAR,
            foreground=INK,
            anchor="w",
            padding=(14, 9),
            font=self.f_ui,
        )
        style.map(
            "Nav.TButton",
            background=[("active", SIDEBAR_SOFT), ("pressed", SIDEBAR_SOFT)],
        )
        style.configure(
            "Done.TLabel",
            background=SIDEBAR,
            foreground=ACCENT,
            font=self.f_ui_bold,
        )
        style.configure(
            "Muted.TLabel", background=PAPER, foreground=MUTED, font=self.f_small
        )
        style.configure(
            "MutedSide.TLabel",
            background=SIDEBAR,
            foreground=MUTED,
            font=self.f_small,
        )
        style.configure(
            "Hint.TLabel",
            background=WARN_SOFT,
            foreground="#6a5320",
            font=self.f_ui,
        )
        style.configure(
            "Progress.Horizontal.TProgressbar",
            background=ACCENT,
            troughcolor=SIDEBAR,
            bordercolor=SIDEBAR,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=6,
        )

    def _build(self) -> None:
        self._build_header()

        body = tk.Frame(self, bg=PAPER)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        self.content = tk.Frame(body, bg=PAPER)
        self.content.pack(side="left", fill="both", expand=True, padx=(0, 0))

        self.pages = {}
        self.pages["lesson"] = self._build_lesson_page(self.content)
        self.pages["playground"] = self._build_playground_page(self.content)
        self.pages["apps"] = self._build_apps_page(self.content)
        self.pages["tutor"] = self._build_tutor_page(self.content)
        self.pages["reference"] = self._build_reference_page(self.content)
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_statusbar()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=PAPER, height=76)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=PAPER)
        left.pack(side="left", padx=22, pady=12)

        title = tk.Label(
            left, text="Bolo", bg=PAPER, fg=ACCENT, font=self.f_h1
        )
        title.pack(side="left")
        subtitle = tk.Label(
            left,
            text="   learn by doing",
            bg=PAPER,
            fg=MUTED,
            font=self.f_ui,
        )
        subtitle.pack(side="left", pady=(8, 0))

        right = tk.Frame(header, bg=PAPER)
        right.pack(side="right", padx=22, pady=14)

        self.progress_label = ttk.Label(
            right, text="", style="Muted.TLabel", background=PAPER
        )
        self.progress_label.configure(font=self.f_small)
        self.progress_label.pack(side="left", padx=(0, 12))

        self.progress_bar = ttk.Progressbar(
            right,
            style="Progress.Horizontal.TProgressbar",
            length=150,
            maximum=len(self.lessons),
        )
        self.progress_bar.pack(side="left")

        rule = tk.Frame(self, bg=RULE, height=1)
        rule.pack(fill="x")

    def _build_sidebar(self, parent: tk.Widget) -> None:
        side = tk.Frame(parent, bg=SIDEBAR, width=272)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(
            side,
            text="THE COURSE",
            bg=SIDEBAR,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(fill="x", padx=20, pady=(20, 8))

        self.nav = tk.Listbox(
            side,
            bg=SIDEBAR,
            fg=INK,
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=0,
            borderwidth=0,
            font=self.f_ui,
            cursor="hand2",
        )
        self.nav.pack(fill="both", expand=True, padx=(8, 4), pady=0)
        self.nav.bind("<<ListboxSelect>>", self._on_nav_select)

        tk.Frame(side, bg=RULE, height=1).pack(fill="x", padx=16, pady=12)

        tk.Label(
            side,
            text="TOOLS",
            bg=SIDEBAR,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 6))

        ttk.Button(
            side,
            text="App Studio",
            style="Nav.TButton",
            command=self.show_apps,
        ).pack(fill="x", padx=12, pady=2)
        ttk.Button(
            side,
            text="Playground",
            style="Nav.TButton",
            command=self.show_playground,
        ).pack(fill="x", padx=12, pady=2)
        ttk.Button(
            side,
            text="Ask the tutor - local AI",
            style="Nav.TButton",
            command=self.show_tutor,
        ).pack(fill="x", padx=12, pady=2)
        ttk.Button(
            side,
            text="Reference - every word",
            style="Nav.TButton",
            command=self.show_reference,
        ).pack(fill="x", padx=12, pady=2)

        ttk.Button(
            side,
            text="Open sandbox folder",
            style="Nav.TButton",
            command=self._open_sandbox,
        ).pack(fill="x", padx=12, pady=(2, 12))

        bottom = tk.Frame(side, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 14))

        ttk.Button(
            bottom,
            text="Reset progress",
            style="Ghost.TButton",
            command=self._reset_progress,
        ).pack(fill="x")

        tk.Label(
            bottom,
            text="Your code is saved as you go.",
            bg=SIDEBAR,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(8, 0))

    # -- pages --------------------------------------------------------------
    def _build_lesson_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=PAPER)

        split = ttk.PanedWindow(page, orient="vertical")
        split.pack(fill="both", expand=True, padx=18, pady=(16, 0))

        # explanation
        doc_card = tk.Frame(
            split, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        doc_head = tk.Frame(doc_card, bg=PANEL)
        doc_head.pack(fill="x", padx=20, pady=(14, 0))

        self.lesson_kicker = tk.Label(
            doc_head, text="", bg=PANEL, fg=ACCENT, font=self.f_small
        )
        self.lesson_kicker.pack(anchor="w")
        self.lesson_title = tk.Label(
            doc_head, text="", bg=PANEL, fg=INK, font=self.f_h2
        )
        self.lesson_title.pack(anchor="w", pady=(2, 0))

        self.doc = tk.Text(
            doc_card,
            wrap="word",
            bg=PANEL,
            fg=INK,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=20,
            pady=10,
            spacing1=1,
            spacing3=3,
            cursor="arrow",
        )
        self.doc.pack(fill="both", expand=True, pady=(6, 12))
        self._style_doc(self.doc)
        doc_card.pack(fill="both", expand=True) if False else None
        split.add(doc_card, weight=3)

        # task strip
        task_wrap = tk.Frame(page, bg=WARN_SOFT)
        task_wrap.pack(fill="x", padx=18, pady=(10, 0))
        tk.Label(
            task_wrap, text="TASK", bg=WARN_SOFT, fg="#8a6a1f", font=self.f_small
        ).pack(side="left", padx=(16, 8), pady=8)
        self.task_label = tk.Label(
            task_wrap,
            text="",
            bg=WARN_SOFT,
            fg="#5f4a18",
            font=self.f_ui,
            anchor="w",
            justify="left",
        )
        self.task_label.pack(side="left", fill="x", expand=True, padx=(0, 16), pady=8)

        # editor + output
        work = ttk.PanedWindow(page, orient="vertical")
        work.pack(fill="both", expand=True, padx=18, pady=(8, 12))

        editor_card = tk.Frame(
            work, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        bar = tk.Frame(editor_card, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=(10, 6))

        ttk.Button(
            bar, text="Run", style="Accent.TButton", command=self.run_lesson
        ).pack(side="left")
        ttk.Button(
            bar, text="Check", style="TButton", command=self.check_lesson
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            bar, text="Show answer", style="Ghost.TButton", command=self.show_answer
        ).pack(side="right")
        ttk.Button(
            bar, text="Reset code", style="Ghost.TButton", command=self.reset_code
        ).pack(side="right", padx=(0, 6))

        self.run_hint = tk.Label(
            bar, text="F5 to run", bg=PANEL, fg=MUTED, font=self.f_small
        )
        self.run_hint.pack(side="left", padx=(14, 0))

        self.editor = self._make_editor(editor_card, self.f_code)
        self.editor.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._bind_editor(self.editor, self.run_lesson, self.check_lesson)

        work.add(editor_card, weight=4)

        out_card = tk.Frame(work, bg=CONSOLE_BG)
        out_bar = tk.Frame(out_card, bg=CONSOLE_BG)
        out_bar.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(
            out_bar, text="OUTPUT", bg=CONSOLE_BG, fg=CONSOLE_MUTED, font=self.f_small
        ).pack(side="left")
        self.lesson_verdict = tk.Label(
            out_bar, text="", bg=CONSOLE_BG, fg=OK, font=self.f_ui_bold
        )
        self.lesson_verdict.pack(side="right")

        self.out = self._make_console(out_card)
        self.out.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        work.add(out_card, weight=2)

        page.after(120, lambda: self._set_sashes(split, work, doc_card, editor_card))
        return page

    def _set_sashes(self, split, work, doc_card, editor_card) -> None:
        try:
            split.sashpos(0, 300)
            work.sashpos(0, 360)
        except tk.TclError:
            pass

    def _build_playground_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=PAPER)

        head = tk.Frame(page, bg=PAPER)
        head.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(
            head, text="Playground", bg=PAPER, fg=INK, font=self.f_h2
        ).pack(anchor="w")
        tk.Label(
            head,
            text=(
                "One live session: names you create stay until you press "
                "Restart. File work happens in app_sandbox."
            ),
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        bar = tk.Frame(page, bg=PAPER)
        bar.pack(fill="x", padx=20, pady=(8, 0))
        ttk.Button(
            bar, text="Run", style="Accent.TButton", command=self.run_playground
        ).pack(side="left")
        ttk.Button(
            bar, text="Restart session", style="TButton", command=self.restart_playground
        ).pack(side="left", padx=(8, 0))

        self.snippet_var = tk.StringVar(value="Load an example...")
        snippets = ttk.Combobox(
            bar,
            textvariable=self.snippet_var,
            values=[name for name, _ in PLAYGROUND_SNIPPETS],
            state="readonly",
            width=24,
            font=self.f_ui,
        )
        snippets.pack(side="right")
        snippets.bind("<<ComboboxSelected>>", self._load_snippet)

        split = ttk.PanedWindow(page, orient="vertical")
        split.pack(fill="both", expand=True, padx=20, pady=(10, 16))

        editor_card = tk.Frame(
            split, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        self.play_editor = self._make_editor(editor_card, self.f_code)
        self.play_editor.pack(fill="both", expand=True, padx=10, pady=10)
        self._bind_editor(self.play_editor, self.run_playground, None)
        saved = self.progress.get("playground")
        self.play_editor.insert("1.0", saved if isinstance(saved, str) else "say(\"hello\")\n")
        self._paint(self.play_editor)
        split.add(editor_card, weight=3)

        out_card = tk.Frame(split, bg=CONSOLE_BG)
        out_bar = tk.Frame(out_card, bg=CONSOLE_BG)
        out_bar.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(
            out_bar,
            text="SESSION",
            bg=CONSOLE_BG,
            fg=CONSOLE_MUTED,
            font=self.f_small,
        ).pack(side="left")
        ttk.Button(
            out_bar, text="Copy", style="Ghost.TButton", command=self._copy_output
        ).pack(side="right")
        self.play_out = self._make_console(out_card)
        self.play_out.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        split.add(out_card, weight=2)

        page.after(160, lambda: self._safe_sash(split, 330))
        return page

    def _build_apps_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=PAPER)

        head = tk.Frame(page, bg=PAPER)
        head.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(
            head, text="App Studio", bg=PAPER, fg=INK, font=self.f_h2
        ).pack(anchor="w")
        tk.Label(
            head,
            text=(
                "Write a Bolo program and open a real desktop window. "
                "Close the window to come back. File work stays in app_sandbox."
            ),
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        bar = tk.Frame(page, bg=PAPER)
        bar.pack(fill="x", padx=20, pady=(8, 0))
        ttk.Button(
            bar, text="Open app", style="Accent.TButton", command=self.run_app_studio
        ).pack(side="left")
        ttk.Button(
            bar, text="Stop app", style="TButton", command=self.stop_app
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            bar, text="Clear output", style="Ghost.TButton", command=self._clear_app_output
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            bar, text="Copy", style="Ghost.TButton", command=self._copy_app_code
        ).pack(side="left", padx=(4, 0))

        self.app_template_var = tk.StringVar(value="Load a template...")
        templates = ttk.Combobox(
            bar,
            textvariable=self.app_template_var,
            values=[name for name, _ in APP_TEMPLATES],
            state="readonly",
            width=22,
            font=self.f_ui,
        )
        templates.pack(side="right")
        templates.bind("<<ComboboxSelected>>", self._load_app_template)

        self.app_status = tk.Label(
            page, text="", bg=PAPER, fg=MUTED, font=self.f_small, anchor="w"
        )
        self.app_status.pack(fill="x", padx=20, pady=(8, 2))

        split = ttk.PanedWindow(page, orient="vertical")
        split.pack(fill="both", expand=True, padx=20, pady=(2, 16))

        editor_card = tk.Frame(
            split, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        self.app_editor = self._make_editor(editor_card, self.f_code)
        self.app_editor.pack(fill="both", expand=True, padx=10, pady=10)
        self.app_editor.insert("1.0", APP_TEMPLATES[0][1])
        saved_app = self.progress.get("app_studio")
        if isinstance(saved_app, str) and saved_app.strip():
            self.app_editor.delete("1.0", "end")
            self.app_editor.insert("1.0", saved_app)
        self._paint(self.app_editor)
        self._bind_editor(self.app_editor, self.run_app_studio, None)
        split.add(editor_card, weight=4)

        out_card = tk.Frame(split, bg=CONSOLE_BG)
        out_bar = tk.Frame(out_card, bg=CONSOLE_BG)
        out_bar.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(
            out_bar,
            text="APP OUTPUT",
            bg=CONSOLE_BG,
            fg=CONSOLE_MUTED,
            font=self.f_small,
        ).pack(side="left")
        self.app_out = self._make_console(out_card)
        self.app_out.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        split.add(out_card, weight=1)

        page.after(160, lambda: self._safe_sash(split, 430))
        return page

    def _build_tutor_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=PAPER)

        head = tk.Frame(page, bg=PAPER)
        head.pack(fill="x", padx=20, pady=(16, 4))
        left = tk.Frame(head, bg=PAPER)
        left.pack(side="left")
        tk.Label(
            left, text="Tutor", bg=PAPER, fg=INK, font=self.f_h2
        ).pack(anchor="w")
        tk.Label(
            left,
            text=(
                "A private helper running on this machine through Ollama. "
                "It can see the lesson and your code."
            ),
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        self.tutor_status = tk.Label(
            head, text="Checking local AI...", bg=PAPER, fg=MUTED, font=self.f_small
        )
        self.tutor_status.pack(side="right", pady=(8, 0))

        chat_card = tk.Frame(
            page, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        chat_card.pack(fill="both", expand=True, padx=20, pady=(10, 6))

        self.tutor_log = tk.Text(
            chat_card,
            wrap="word",
            bg=PANEL,
            fg=INK,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=20,
            pady=16,
            spacing1=2,
            spacing3=4,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(chat_card, command=self.tutor_log.yview)
        self.tutor_log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tutor_log.pack(fill="both", expand=True)
        self.tutor_log.tag_configure(
            "you", font=self.f_ui_bold, foreground=ACCENT, spacing1=10
        )
        self.tutor_log.tag_configure("tutor", font=self.f_ui_bold, foreground=INK, spacing1=10)
        self.tutor_log.tag_configure("body", font=self.f_ui, foreground=INK, spacing3=4)
        self.tutor_log.tag_configure("muted", font=self.f_small, foreground=MUTED)
        self.tutor_log.tag_configure("err", font=self.f_ui, foreground="#a33b2a")
        self.tutor_log.configure(state="disabled")
        self._append_tutor(
            "Ask about the lesson you are on, paste an error, or say "
            "\"check my code\".\nThe first answer can take half a minute while "
            "the model wakes up.\n",
            "muted",
        )

        composer = tk.Frame(page, bg=PAPER)
        composer.pack(fill="x", padx=20, pady=(0, 14))

        quick = tk.Frame(composer, bg=PAPER)
        quick.pack(fill="x", pady=(0, 4))
        ttk.Button(
            quick, text="Hint", style="Ghost.TButton",
            command=lambda: self.ask_tutor(
                "Give me one hint for this lesson. Do not give the full answer."
            ),
        ).pack(side="left")
        ttk.Button(
            quick, text="Check my code", style="Ghost.TButton",
            command=lambda: self.ask_tutor(
                "Look at my code. Tell me briefly what still needs doing, "
                "without pasting a whole solution."
            ),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            quick, text="Explain last error", style="Ghost.TButton",
            command=self._ask_about_error,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            quick, text="Clear chat", style="Ghost.TButton", command=self.clear_tutor
        ).pack(side="left", padx=(6, 0))

        self.tutor_include = tk.BooleanVar(value=True)
        tk.Checkbutton(
            quick,
            text="Include my lesson and code",
            variable=self.tutor_include,
            bg=PAPER,
            fg=MUTED,
            activebackground=PAPER,
            activeforeground=INK,
            font=self.f_small,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        ).pack(side="right")

        box = tk.Frame(
            composer, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        box.pack(fill="x")
        self.tutor_input = tk.Text(
            box,
            height=3,
            wrap="word",
            bg="#fcfbf8",
            fg=INK,
            insertbackground=ACCENT,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
        )
        self.tutor_input.pack(side="left", fill="both", expand=True)
        self.tutor_input.bind("<Control-Return>", lambda _e: (self.ask_tutor(), "break")[1])

        self.tutor_ask = ttk.Button(
            composer, text="Ask", style="Accent.TButton", command=self.ask_tutor
        )
        self.tutor_ask.pack(side="right", padx=(8, 0), pady=(8, 0))

        self.tutor_note = tk.Label(
            composer, text="", bg=PAPER, fg=MUTED, font=self.f_small, anchor="w"
        )
        self.tutor_note.pack(fill="x", pady=(4, 0))

        return page

    def _build_reference_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=PAPER)

        head = tk.Frame(page, bg=PAPER)
        head.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(
            head, text="Reference", bg=PAPER, fg=INK, font=self.f_h2
        ).pack(anchor="w")
        tk.Label(
            head,
            text="Every builtin and every piece of syntax. Search it when you forget a word.",
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        search_row = tk.Frame(page, bg=PAPER)
        search_row.pack(fill="x", padx=20, pady=(10, 4))

        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_row, textvariable=self.search_var, font=self.f_ui)
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, "")
        self.search_var.trace_add("write", lambda *_: self._render_reference())

        ttk.Button(
            search_row, text="Clear", style="Ghost.TButton", command=lambda: self.search_var.set("")
        ).pack(side="left", padx=(8, 0))

        self.ref_count = tk.Label(
            search_row, text="", bg=PAPER, fg=MUTED, font=self.f_small
        )
        self.ref_count.pack(side="left", padx=(12, 0))

        card = tk.Frame(page, bg=PANEL, highlightbackground=RULE, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=20, pady=(6, 16))

        self.ref = tk.Text(
            card,
            wrap="word",
            bg=PANEL,
            fg=INK,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=22,
            pady=16,
            spacing1=1,
            spacing3=4,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(card, command=self.ref.yview)
        self.ref.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.ref.pack(fill="both", expand=True)
        self._style_doc(self.ref, mono_bg="#f4f2ec")
        self._render_reference()
        return page

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=PAPER)
        bar.pack(fill="x", side="bottom")
        tk.Frame(bar, bg=RULE, height=1).pack(fill="x")
        self.status = tk.Label(
            bar,
            text="Pick a lesson on the left. Everything you type is saved.",
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
        )
        self.status.pack(fill="x", padx=22, pady=6)

    # -- widget helpers -----------------------------------------------------
    def _make_editor(self, parent: tk.Widget, font: tkfont.Font) -> tk.Text:
        wrap = tk.Frame(parent, bg=PANEL)
        text = tk.Text(
            wrap,
            wrap="none",
            bg="#fcfbf8",
            fg=INK,
            insertbackground=ACCENT,
            selectbackground="#cfe3d8",
            font=font,
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            undo=True,
            spacing1=1,
            spacing3=2,
            tabs="2c",
        )
        yscroll = ttk.Scrollbar(wrap, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        text.tag_configure("comment", foreground="#8b9097", font=(font.cget("family"), font.cget("size"), "italic"))
        text.tag_configure("string", foreground="#2a7f62")
        text.tag_configure("number", foreground="#a9601c")
        text.tag_configure("keyword", foreground="#8b3f9e")
        text.tag_configure("builtin", foreground="#2a5f9e")
        text.tag_configure("pipe", foreground="#b04a3c")
        text.tag_configure(
            "errline", background=HIGHLIGHT, relief="flat"
        )

        text.tag_raise("errline")
        return text

    def _make_console(self, parent: tk.Widget) -> tk.Text:
        wrap = tk.Frame(parent, bg=CONSOLE_BG)
        text = tk.Text(
            wrap,
            wrap="word",
            bg=CONSOLE_BG,
            fg=CONSOLE_FG,
            font=self.f_code_small,
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=10,
            spacing1=1,
            spacing3=2,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(wrap, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.tag_configure("muted", foreground=CONSOLE_MUTED)
        text.tag_configure("err", foreground=ERR)
        text.tag_configure("ok", foreground=OK)
        text.tag_configure("echo", foreground="#7fa8d9")
        text.configure(state="disabled")
        text.wrap_widget = wrap  # type: ignore[attr-defined]
        return text

    def _bind_editor(self, widget: tk.Text, run, check) -> None:
        widget.bind("<Tab>", self._on_tab)
        widget.bind("<Return>", self._on_return)
        widget.bind("<Control-Return>", lambda _e: (run(), "break")[1])
        widget.bind("<F5>", lambda _e: (run(), "break")[1])
        if check is not None:
            widget.bind("<Control-Shift-Return>", lambda _e: (check(), "break")[1])
        widget.bind("<KeyRelease>", lambda _e: self._schedule_paint(widget))
        widget.bind("<<Paste>>", lambda _e: (self.after(1, lambda: self._paint(widget)), None)[1])

    def _on_tab(self, event) -> str:
        event.widget.insert("insert", "  ")
        return "break"

    def _on_return(self, event) -> str:
        widget = event.widget
        line = widget.get("insert linestring start", "insert")
        indent = re.match(r"[ ]*", line).group(0)
        extra = "  " if line.rstrip().endswith("{") else ""
        widget.insert("insert", "\n" + indent + extra)
        widget.see("insert")
        return "break"

    def _schedule_paint(self, widget: tk.Text) -> None:
        if self._highlight_job:
            try:
                self.after_cancel(self._highlight_job)
            except ValueError:
                pass
        self._highlight_job = self.after(90, lambda: self._paint(widget))

    # -- syntax colours -----------------------------------------------------
    def _paint(self, widget: tk.Text) -> None:
        data = widget.get("1.0", "end-1c")
        for tag in ("comment", "string", "number", "keyword", "builtin", "pipe"):
            widget.tag_remove(tag, "1.0", "end")
        for match in TOKEN_RE.finditer(data):
            kind = match.lastgroup
            if not kind:
                continue
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            widget.tag_add(kind, start, end)

    # -- document rendering -------------------------------------------------
    def _style_doc(self, widget: tk.Text, mono_bg: str = "#f4f2ec") -> None:
        widget.tag_configure("h2", font=self.f_h2, foreground=INK, spacing1=10, spacing3=4)
        widget.tag_configure("body", font=self.f_ui, foreground=INK, spacing3=3)
        widget.tag_configure(
            "code",
            font=self.f_code_small,
            background=mono_bg,
            foreground="#2f3439",
            lmargin1=14,
            lmargin2=14,
            spacing1=3,
            spacing3=3,
        )
        widget.tag_configure("inline", font=self.f_code_small, background=mono_bg, foreground="#2f3439")
        widget.tag_configure("bullet", font=self.f_ui, lmargin1=6, lmargin2=20, spacing3=2)
        widget.configure(state="disabled")

    def _render_doc(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for line in text.splitlines():
            if line.startswith("## "):
                widget.insert("end", line[3:].strip() + "\n", "h2")
            elif line.startswith("    "):
                widget.insert("end", line[4:] + "\n", "code")
            elif line.startswith("- "):
                self._insert_inline(widget, "•  " + line[2:], "bullet")
                widget.insert("end", "\n", "bullet")
            elif not line.strip():
                widget.insert("end", "\n")
            else:
                self._insert_inline(widget, line, "body")
                widget.insert("end", "\n", "body")
        widget.configure(state="disabled")
        widget.yview_moveto(0)

    def _insert_inline(self, widget: tk.Text, text: str, base: str) -> None:
        parts = text.split("`")
        for index, part in enumerate(parts):
            if not part:
                continue
            widget.insert("end", part, "inline" if index % 2 else base)

    # -- reference ----------------------------------------------------------
    def _render_reference(self) -> None:
        query = self.search_var.get().strip().lower()
        widget = self.ref
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        shown = 0
        for group, entries in REFERENCE:
            matches = [
                entry
                for entry in entries
                if not query
                or query in entry[0].lower()
                or query in entry[1].lower()
            ]
            if not matches:
                continue
            widget.insert("end", group.upper() + "\n", "group")
            for signature, description, example in matches:
                shown += 1
                widget.insert("end", signature + "\n", "sig")
                widget.insert("end", description + "\n", "body")
                for line in example.splitlines():
                    widget.insert("end", "    " + line + "\n", "code")
                widget.insert("end", "\n")

        if shown == 0:
            widget.insert(
                "end",
                "No word matches that search.\n\nTry: text, list, file, map, sort, if, for",
                "body",
            )

        widget.tag_configure("group", font=self.f_small, foreground=ACCENT, spacing1=14, spacing3=6)
        widget.tag_configure("sig", font=self.f_code, foreground=INK, spacing1=6)
        widget.configure(state="disabled")
        widget.yview_moveto(0)
        self.ref_count.configure(text=f"{shown} entries" if query else "")

    # -- navigation ---------------------------------------------------------
    def _refresh_sidebar(self) -> None:
        self.nav.delete(0, "end")
        for index, lesson in enumerate(self.lessons):
            done = self._is_done(lesson.id)
            mark = "✔" if done else " "
            self.nav.insert("end", f" {mark}  {index + 1:02d}   {lesson.title}")
        if self.view == "lesson":
            self.nav.selection_set(self.current)
            self.nav.see(self.current)

    def _refresh_progress(self) -> None:
        done = sum(1 for lesson in self.lessons if self._is_done(lesson.id))
        total = len(self.lessons)
        self.progress_label.configure(text=f"{done} of {total} lessons done")
        self.progress_bar.configure(maximum=total, value=done)

    def _is_done(self, lesson_id: str) -> bool:
        entry = self.progress.get("lessons", {}).get(lesson_id)
        return bool(isinstance(entry, dict) and entry.get("done"))

    def _on_nav_select(self, _event=None) -> None:
        selection = self.nav.curselection()
        if not selection:
            return
        self._select_lesson(int(selection[0]))

    def _select_lesson(self, index: int) -> None:
        index = max(0, min(index, len(self.lessons) - 1))
        self._save_current_code()
        self.current = index
        lesson = self.lessons[index]
        self.view = "lesson"

        self.lesson_kicker.configure(text=f"LESSON {index + 1} OF {len(self.lessons)}")
        self.lesson_title.configure(text=lesson.title + "  ·  " + lesson.subtitle)
        self._render_doc(self.doc, lesson.body)
        self.task_label.configure(text=lesson.task)

        code = self._saved_code(lesson) or lesson.starter
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        self.editor.tag_remove("errline", "1.0", "end")
        self.editor.edit_reset()
        self._paint(self.editor)
        self._clear_console(self.out)
        self.lesson_verdict.configure(text="")
        self._show_page("lesson")
        self.editor.focus_set()

        self.progress["last_lesson"] = index
        self._save_progress()
        self._refresh_sidebar()

    def show_playground(self) -> None:
        self._save_current_code()
        self.view = "playground"
        self.nav.selection_clear(0, "end")
        self._show_page("playground")
        self.play_editor.focus_set()

    def show_apps(self) -> None:
        self._save_current_code()
        self.view = "apps"
        self.nav.selection_clear(0, "end")
        self._show_page("apps")
        self.app_editor.focus_set()

    def show_tutor(self, context: str | None = None) -> None:
        if context is not None:
            self._tutor_context = context
        elif self.view in ("lesson", "apps"):
            self._tutor_context = self.view
        self._save_current_code()
        self.view = "tutor"
        self.nav.selection_clear(0, "end")
        self._show_page("tutor")
        self._check_tutor()
        self.tutor_input.focus_set()

    def show_reference(self) -> None:
        self._save_current_code()
        self.view = "reference"
        self.nav.selection_clear(0, "end")
        self._show_page("reference")
        self._render_reference()

    def _show_page(self, name: str) -> None:
        self.pages[name].tkraise()
        if name == "lesson":
            lesson = self.lessons[self.current]
            self._set_status(
                f"Lesson {self.current + 1}: {lesson.title}.  "
                "Run it, then press Check."
            )
        elif name == "playground":
            self._set_status(
                "Playground: one session, names stick around. Press Restart to begin clean."
            )
        elif name == "apps":
            self._set_status(
                "App Studio: write a window, press Open app, then close the window to return."
            )
        elif name == "tutor":
            self._set_status(
                "Tutor: a local AI that knows Bolo and can see this lesson."
            )
        else:
            self._set_status("Reference: search for a word like text, list, sort or file.")

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    # -- actions ------------------------------------------------------------
    def run_lesson(self) -> None:
        lesson = self.lessons[self.current]
        source = self.editor.get("1.0", "end-1c")
        self._save_current_code()

        if lesson.gui:
            self._clear_console(self.out)
            self.lesson_verdict.configure(text="", fg=CONSOLE_MUTED)
            if self._launch_app(source, "lesson") is not None:
                self._append_console(
                    self.out,
                    "Opened your app in its own window.\n"
                    "Close that window to come back here.\n",
                    "muted",
                )
                self.lesson_verdict.configure(text="app opened", fg=OK)
                self._set_status(
                    "Your app is open. Close its window to return, then press Check."
                )
            return

        self._busy()
        result = run_source(source, reset_first=True)
        self.last_error = result.error
        self._show_result(self.out, result, echo=False)
        self._mark_error_line(self.editor, result.error_line)
        if result.error:
            self.lesson_verdict.configure(text="stopped with an error", fg=ERR)
            self._set_status("Read the message at the bottom. It names the fix.")
        elif result.output.strip():
            self.lesson_verdict.configure(text="ran", fg=CONSOLE_MUTED)
            self._set_status("Now press Check to see whether the task is done.")
        else:
            self.lesson_verdict.configure(text="ran, printed nothing", fg=CONSOLE_MUTED)
            self._set_status("Your code ran, but nothing was printed. Try say(...).")

    def check_lesson(self) -> None:
        lesson = self.lessons[self.current]
        source = self.editor.get("1.0", "end-1c")
        self._save_current_code()

        if lesson.gui:
            self._check_app_lesson(lesson, source)
            return

        self._busy()
        result = run_source(source, reset_first=True)
        self.last_error = result.error
        self._show_result(self.out, result, echo=False)
        self._mark_error_line(self.editor, result.error_line)

        if result.error:
            self.lesson_verdict.configure(text="not yet", fg=ERR)
            self._set_status("Not yet - fix the error first, then press Check again.")
            self._append_console(self.out, "\nNot yet: the code stopped with an error.\n", "err")
            return

        missing = [wanted for wanted in lesson.must if wanted not in result.output]
        if missing:
            self.lesson_verdict.configure(text="not yet", fg="#f3c56b")
            self._append_console(self.out, "\nNot yet. Still missing:\n", "err")
            for wanted in missing:
                self._append_console(self.out, f"    {wanted}\n", "err")
            self._set_status("Not yet - the lines above are not in the output.")
            return

        self._complete(lesson)

    def _check_app_lesson(self, lesson: Lesson, source: str) -> None:
        """Check a window lesson without opening a window.

        We read the code for the parts that make an app real (a window, an
        input, a button, show) and make sure it parses. Running it here would
        open a window and block the learning app until it was closed.
        """
        self._clear_console(self.out)
        try:
            bolo.parse(source)
        except bolo.BoloError as err:
            self.last_error = bolo.format_error(source, "your code", err)
            self._append_console(self.out, self.last_error + "\n", "err")
            self._mark_error_line(self.editor, err.line)
            self.lesson_verdict.configure(text="not yet", fg=ERR)
            self._set_status("Not yet - fix the error first, then press Check again.")
            return

        self.last_error = None
        missing = [wanted for wanted in lesson.code_must if wanted not in source]
        if missing:
            self.lesson_verdict.configure(text="not yet", fg="#f3c56b")
            self._append_console(self.out, "\nNot yet. Your app still needs:\n", "err")
            for wanted in missing:
                self._append_console(self.out, f"    {wanted}\n", "err")
            self._set_status(
                "Add the missing parts above. Press Run to open the window."
            )
            return

        self._append_console(
            self.out,
            "This app has a window, a heading, an input, a button, and show(win).\n",
            "muted",
        )
        self._complete(lesson)

    def _complete(self, lesson: Lesson) -> None:
        self.progress.setdefault("lessons", {}).setdefault(lesson.id, {})
        self.progress["lessons"][lesson.id]["done"] = True
        self._save_current_code()
        self._save_progress()
        self._refresh_sidebar()
        self._refresh_progress()
        self.lesson_verdict.configure(text="✔ passed", fg=OK)
        self._append_console(self.out, "\n✔ Passed. This lesson is done.\n", "ok")

        next_index = self.current + 1
        if next_index < len(self.lessons):
            nxt = self.lessons[next_index]
            self._append_console(
                self.out,
                f"Next: lesson {next_index + 1} - {nxt.title}\n",
                "muted",
            )
            self._set_status(
                f"Passed. Next up: lesson {next_index + 1}, {nxt.title}."
            )
        else:
            self._append_console(
                self.out,
                "That was the last lesson. The Playground is yours now.\n",
                "ok",
            )
            self._set_status("All 15 lessons done. Try the Playground or App Studio.")

    def show_answer(self) -> None:
        lesson = self.lessons[self.current]
        if not lesson.solution:
            return
        if not messagebox.askyesno(
            "Show the answer?",
            "This replaces what is in the editor with a working answer.\n\n"
            "Your current code is lost. Continue?",
            parent=self,
        ):
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", lesson.solution)
        self._paint(self.editor)
        self._set_status("Answer loaded. Press Run, then Check to see it pass.")

    def reset_code(self) -> None:
        lesson = self.lessons[self.current]
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", lesson.starter)
        self.em_clear_errors()
        self._paint(self.editor)
        self._set_status("Back to the starting code for this lesson.")

    def em_clear_errors(self) -> None:
        self.editor.tag_remove("errline", "1.0", "end")

    def run_playground(self) -> None:
        source = self.play_editor.get("1.0", "end-1c")
        if not source.strip():
            return
        self._busy()
        self._append_console(self.play_out, "\n>>> ", "echo")
        for line in source.splitlines():
            self._append_console(self.play_out, line + "\n", "echo")
        result = run_source(source, interp=self.play_interp, reset_first=False)
        if result.output:
            self._append_console(self.play_out, result.output)
        if result.error:
            self._append_console(self.play_out, result.error + "\n", "err")
        elif result.value is not None:
            self._append_console(self.play_out, bolo.repr_value(result.value) + "\n")
        self.progress["playground"] = source
        self._save_progress()
        self._set_status("Session kept. Names stay until you press Restart session.")

    def restart_playground(self) -> None:
        self.play_interp = bolo.Interp()
        reset_sandbox()
        self._clear_console(self.play_out)
        self._append_console(
            self.play_out, "Fresh session. Every name is gone.\n", "muted"
        )
        self._set_status("Fresh playground session.")

    def _load_snippet(self, _event=None) -> None:
        name = self.snippet_var.get()
        for snippet_name, code in PLAYGROUND_SNIPPETS:
            if snippet_name == name:
                self.play_editor.delete("1.0", "end")
                self.play_editor.insert("1.0", code)
                self._paint(self.play_editor)
                self.snippet_var.set("Load an example...")
                self._set_status(f"Loaded '{snippet_name}'. Press Run.")
                return

    # -- app studio ---------------------------------------------------------
    def _load_app_template(self, _event=None) -> None:
        name = self.app_template_var.get()
        for template_name, code in APP_TEMPLATES:
            if template_name == name:
                self.app_editor.delete("1.0", "end")
                self.app_editor.insert("1.0", code)
                self._paint(self.app_editor)
                self.app_template_var.set("Load a template...")
                self.app_status.configure(
                    text=f"Loaded '{template_name}'. Press Open app to try it.",
                    fg=MUTED,
                )
                return

    def run_app_studio(self) -> None:
        source = self.app_editor.get("1.0", "end-1c")
        if not source.strip():
            self.app_status.configure(text="Write some app code first.", fg=MUTED)
            return
        self._launch_app(source, "apps")

    def _bolo_command(self, script: Path, exe: Path) -> list[str]:
        """Start Bolo from source, or from the bolo.exe shipped beside a build."""
        if getattr(sys, "frozen", False):
            folder = Path(sys.executable).resolve().parent
            for name in ("bolo.exe", "bolo"):
                candidate = folder / name
                if candidate.exists():
                    return [str(candidate), str(script)]
            return [str(exe), str(script)]
        return [str(exe), str(APP_DIR / "bolo.py"), str(script)]

    def _launch_app(self, source: str, origin: str):
        """Start a real Bolo app in its own process so this window stays alive."""
        if self._app_proc is not None and self._app_proc.poll() is None:
            self.app_status.configure(
                text="An app is already open. Close it, or press Stop app.",
                fg="#8a6a1f",
            )
            return None

        reset_sandbox()
        script = SANDBOX / "app_preview.bolo"
        script.write_text(source, encoding="utf-8")
        log = SANDBOX / "app_output.txt"

        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            candidate = exe.with_name("python.exe")
            if candidate.exists():
                exe = candidate

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            with open(log, "w", encoding="utf-8") as handle:
                proc = subprocess.Popen(
                    self._bolo_command(script, exe),
                    cwd=str(SANDBOX),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
        except OSError as exc:
            self.app_status.configure(text=f"Could not start Bolo: {exc}", fg=ERR)
            return None

        self._app_proc = proc
        self._app_log = log
        self._app_origin = origin
        if origin == "apps":
            self._clear_app_output()
            self.app_status.configure(text="Opening the app...", fg=MUTED)
        self._set_status("Opening your app in a separate window. Close it to return.")
        self.after(900, lambda: self._watch_app(proc, log, True))
        return proc

    def _watch_app(self, proc, log: Path, first: bool) -> None:
        if proc is not self._app_proc:
            return

        if proc.poll() is None:
            if first:
                message = "App window opened. Close it when you are done."
                if self._app_origin == "apps":
                    self.app_status.configure(text=message, fg=ACCENT)
            self._app_poll_job = self.after(
                700, lambda: self._watch_app(proc, log, False)
            )
            return

        self._app_proc = None
        try:
            output = log.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            output = ""

        stopped_badly = "bolo:" in output or "Traceback" in output
        if self._app_origin == "apps":
            self._clear_app_output()
            if output:
                self._append_console(
                    self.app_out,
                    output + "\n",
                    "err" if stopped_badly else None,
                )
            if stopped_badly:
                self.app_status.configure(
                    text="The app stopped with a message. Read it below.", fg=ERR
                )
                self._set_status("The app stopped. The message below names the fix.")
            else:
                self.app_status.configure(text="App closed.", fg=MUTED)
                self._set_status("App closed. Change something and open it again.")
            return

        if output:
            self._append_console(
                self.out, "\n" + output + "\n", "err" if stopped_badly else "muted"
            )
        if stopped_badly:
            self.lesson_verdict.configure(text="app stopped with an error", fg=ERR)
            self._set_status("The app stopped. Read its message above.")
        else:
            self.lesson_verdict.configure(text="app closed", fg=CONSOLE_MUTED)
            self._set_status("App closed. Press Check when you are ready.")

    def stop_app(self) -> None:
        if self._app_proc is not None and self._app_proc.poll() is None:
            proc = self._app_proc
            self._app_proc = None
            try:
                proc.terminate()
            except OSError:
                pass
            self.app_status.configure(text="App stopped.", fg=MUTED)
            self._set_status("App stopped.")
            if self._app_origin == "lesson":
                self.lesson_verdict.configure(text="app stopped", fg=CONSOLE_MUTED)
        else:
            self.app_status.configure(text="No app is running.", fg=MUTED)

    def _copy_app_code(self) -> None:
        text = self.app_editor.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("App code copied to the clipboard.")

    def _clear_app_output(self) -> None:
        self._clear_console(self.app_out)

    # -- tutor --------------------------------------------------------------
    def _check_tutor(self) -> None:
        if self.tutor_checked:
            return
        self.tutor_checked = True
        self.tutor_status.configure(text="Checking local AI...", fg=MUTED)
        threading.Thread(target=self._tutor_status_worker, daemon=True).start()

    def _tutor_status_worker(self) -> None:
        model, error = bolo_ai.status()
        self.tutor_queue.put(("status", model, error))

    def _apply_tutor_status(self, model: str | None, error: str | None) -> None:
        if error:
            self.tutor_model = None
            self.tutor_checked = False
            self.tutor_status.configure(text=error.split("\n")[0], fg="#a33b2a")
            self.tutor_note.configure(
                text="The tutor needs Ollama. It is already installed; start it from the Start menu."
            )
            return
        self.tutor_model = model
        self.tutor_status.configure(text=f"Local AI ready - {model}", fg=ACCENT)
        self.tutor_note.configure(text="")

    def ask_tutor(self, prompt: str | None = None) -> None:
        if self.tutor_pending:
            return
        if self.tutor_model is None:
            self._check_tutor()
            self._append_tutor(
                "The local AI is not ready yet. Check the status at the top, "
                "then ask again.\n\n",
                "err",
            )
            return

        question = prompt
        if question is None:
            question = self.tutor_input.get("1.0", "end-1c").strip()
        if not question:
            question = "Give me a hint for this lesson without giving the full answer."
        self.tutor_input.delete("1.0", "end")

        self._append_tutor("You\n", "you")
        self._append_tutor(question + "\n\n", "body")

        if self._tutor_context == "apps":
            title = "App Studio"
            task = "The learner is building a desktop app."
            code = self.app_editor.get("1.0", "end-1c")
        else:
            lesson = self.lessons[self.current]
            title = f"{self.current + 1}. {lesson.title}"
            task = lesson.task
            code = self.editor.get("1.0", "end-1c")

        self.tutor_history.append({"role": "user", "content": question})
        messages = [{"role": "system", "content": bolo_ai.SYSTEM}]
        if self.tutor_include.get():
            messages.append(
                {
                    "role": "system",
                    "content": bolo_ai.context_message(title, task, code),
                }
            )
        messages.extend(self.tutor_history[-10:])

        self.tutor_pending = True
        self.tutor_ask.state(["disabled"])
        self.tutor_note.configure(text="Thinking... the first answer can take half a minute.")
        self._set_status("The local tutor is thinking. Nothing leaves this computer.")
        threading.Thread(
            target=self._tutor_worker,
            args=(messages, self.tutor_model),
            daemon=True,
        ).start()

    def _tutor_worker(self, messages: list[dict], model: str) -> None:
        try:
            answer = bolo_ai.chat(messages, model)
        except bolo_ai.OllamaError as exc:
            self.tutor_queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001 - shown in the chat
            self.tutor_queue.put(("error", f"Unexpected problem: {exc}"))
        else:
            self.tutor_queue.put(("answer", answer))

    def _poll_tutor_queue(self) -> None:
        try:
            while True:
                item = self.tutor_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    self._apply_tutor_status(item[1], item[2])
                elif kind == "answer":
                    self._finish_tutor_answer(item[1])
                elif kind == "error":
                    self._finish_tutor_error(item[1])
        except queue.Empty:
            pass
        self.after(150, self._poll_tutor_queue)

    def _finish_tutor_answer(self, answer: str) -> None:
        self.tutor_pending = False
        self.tutor_ask.state(["!disabled"])
        self.tutor_note.configure(text="")
        self._append_tutor("Tutor\n", "tutor")
        self._append_tutor(answer + "\n\n", "body")
        self.tutor_history.append({"role": "assistant", "content": answer})
        self._set_status("Tutor answered. Ask again whenever you like.")

    def _finish_tutor_error(self, message: str) -> None:
        self.tutor_pending = False
        self.tutor_ask.state(["!disabled"])
        self.tutor_note.configure(text="")
        self._append_tutor("Tutor could not answer\n", "tutor")
        self._append_tutor(message + "\n\n", "err")
        self._set_status("The tutor had a problem. Check that Ollama is running.")

    def _ask_about_error(self) -> None:
        if not self.last_error:
            self._append_tutor(
                "There is no error yet. Press Run on a lesson first, then ask again.\n\n",
                "muted",
            )
            return
        self.ask_tutor(
            "Explain this Bolo error in plain words, then say exactly what to change:\n\n"
            + self.last_error
        )

    def clear_tutor(self) -> None:
        self.tutor_history.clear()
        self.tutor_log.configure(state="normal")
        self.tutor_log.delete("1.0", "end")
        self.tutor_log.configure(state="disabled")
        self._append_tutor(
            "Chat cleared. Ask about the lesson you are on, paste an error, or "
            "say \"check my code\".\n",
            "muted",
        )
        self._set_status("Tutor chat cleared.")

    def _append_tutor(self, text: str, tag: str) -> None:
        self.tutor_log.configure(state="normal")
        self.tutor_log.insert("end", text, tag)
        self.tutor_log.see("end")
        self.tutor_log.configure(state="disabled")

    def _open_sandbox(self) -> None:
        SANDBOX.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(SANDBOX)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - explorer missing is not fatal
            messagebox.showinfo(
                "Sandbox folder",
                f"The lessons run inside:\n\n{SANDBOX}",
                parent=self,
            )

    # -- output helpers -----------------------------------------------------
    def _show_result(self, widget: tk.Text, result: RunResult, echo: bool) -> None:
        self._clear_console(widget)
        if result.output:
            self._append_console(widget, result.output)
        if result.error:
            self._append_console(widget, result.error + "\n", "err")
        if not result.output and not result.error:
            self._append_console(
                widget, "Ran, but nothing was printed. Try say(...).\n", "muted"
            )

    def _clear_console(self, widget: tk.Text) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    def _append_console(self, widget: tk.Text, text: str, tag: str | None = None) -> None:
        widget.configure(state="normal")
        widget.insert("end", text, tag or ())
        widget.see("end")
        widget.configure(state="disabled")

    def _copy_output(self) -> None:
        text = self.play_out.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Session output copied to the clipboard.")

    def _mark_error_line(self, widget: tk.Text, line: int | None) -> None:
        widget.tag_remove("errline", "1.0", "end")
        if line and line > 0:
            widget.tag_add("errline", f"{line}.0", f"{line}.end+1c")
            widget.see(f"{line}.0")

    def _busy(self) -> None:
        self.configure(cursor="watch")
        self.update_idletasks()

    # -- persistence --------------------------------------------------------
    def _load_progress(self) -> dict:
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("lessons", {})
                return data
        except Exception:  # noqa: BLE001 - a missing or broken file just starts fresh
            pass
        return {"lessons": {}}

    def _save_progress(self) -> None:
        temp = PROGRESS_FILE.with_suffix(".tmp")
        try:
            temp.write_text(
                json.dumps(self.progress, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(temp, PROGRESS_FILE)
        except OSError:
            pass

    def _saved_code(self, lesson: Lesson) -> str | None:
        entry = self.progress.get("lessons", {}).get(lesson.id)
        if isinstance(entry, dict):
            code = entry.get("code")
            if isinstance(code, str):
                return code
        return None

    def _save_current_code(self) -> None:
        if self.view == "lesson":
            lesson = self.lessons[self.current]
            code = self.editor.get("1.0", "end-1c")
            self.progress.setdefault("lessons", {}).setdefault(lesson.id, {})
            self.progress["lessons"][lesson.id]["code"] = code
            self._save_progress()
        elif self.view == "apps":
            self.progress["app_studio"] = self.app_editor.get("1.0", "end-1c")
            self._save_progress()

    def _reset_progress(self) -> None:
        if not messagebox.askyesno(
            "Reset progress?",
            "This clears every lesson tick and every piece of code you wrote "
            "in the app.\n\nIt cannot be undone.",
            parent=self,
        ):
            return
        self.progress = {"lessons": {}}
        self._save_progress()
        self._refresh_sidebar()
        self._refresh_progress()
        self._select_lesson(0)
        self._set_status("Progress cleared. Starting from lesson 1.")

    def _on_close(self) -> None:
        self._save_current_code()
        self.progress["playground"] = self.play_editor.get("1.0", "end-1c")
        self._save_progress()
        if self._app_proc is not None and self._app_proc.poll() is None:
            try:
                self._app_proc.terminate()
            except OSError:
                pass
            self._app_proc = None
        self.destroy()

    # -- misc ---------------------------------------------------------------
    def _safe_sash(self, paned: ttk.PanedWindow, position: int) -> None:
        try:
            paned.sashpos(0, position)
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Syntax colouring pattern
# ---------------------------------------------------------------------------

KEYWORDS = [
    "to", "if", "else", "for", "in", "return",
    "and", "or", "not", "is", "true", "false", "nothing", "nil",
]
BUILTIN_NAMES = sorted(set(bolo.BUILTINS), key=len, reverse=True)

TOKEN_RE = re.compile(
    r"(?P<comment>#[^\n]*)"
    r'|(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<keyword>\b(?:" + "|".join(KEYWORDS) + r")\b)"
    r"|(?P<builtin>\b(?:" + "|".join(re.escape(name) for name in BUILTIN_NAMES) + r")\b)"
    r"|(?P<pipe>\|>)"
)


def main() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001 - not fatal, just fuzzy text
        pass

    try:
        app = BoloApp()
        app.mainloop()
    except Exception as exc:  # noqa: BLE001 - pythonw has no console to show this
        import traceback

        detail = traceback.format_exc()
        try:
            (DATA_DIR / "bolo_crash.txt").write_text(detail, encoding="utf-8")
        except OSError:
            pass
        try:
            messagebox.showerror(
                "Bolo could not start",
                f"{exc}\n\nThe full message was saved to bolo_crash.txt.",
            )
        except Exception:  # noqa: BLE001 - no display left to report on
            pass
        raise


if __name__ == "__main__":
    main()
