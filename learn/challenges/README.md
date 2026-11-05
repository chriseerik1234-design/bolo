# Real jobs — after the lessons

You finished the course. Lessons teach one idea each; these give you a whole job
and no instructions beyond a nudge.

Rules of the game:

- **No answers are included here on purpose.** Trying, failing, and reading the
  error is the learning. If you get stuck for more than ten minutes, ask, and
  you get either a hint or the full answer — your choice.
- Each one runs with `.\bolo.cmd learn\challenges\file.bolo`, or by making a
  `.bat` the same way the lessons do.
- Sample data is already in this folder, so you can start immediately.
- Some of these **move or delete real files**. Only point them at
  `learn\challenges\` until you trust them.

Work them in order. The first two are warm-ups; the last two are the sort of
thing people actually get paid for.

---

## 1. The word report (easy)

**Job:** read `sample_notes.txt` and report how many lines, how many words, and
how many characters it has.

```
lines:   13
words:   40
chars:   214
```

**You already know:** `read`, `lines`, `words`, `length`.
**Nudge:** every one of those is a one-line pipeline. Three `say` calls.
**Done when:** the numbers match what Notepad tells you (Notepad shows line
count in its status bar).

---

## 2. The longest word (easy)

**Job:** find the longest word in `sample_notes.txt` and say it.

```
longest word: breakfast
```

**You already know:** `words`, `sortby`, `length`, `last`.
**Nudge:** `sortby` sorts a list by a key. The key here is
`{ length(it) }`. After sorting, which end has the longest?
**Stretch:** say the five longest words instead of one.

---

## 3. Clean the duplicates (medium)

**Job:** `sample_notes.txt` has repeated lines. Write a cleaned copy to
`clean_notes.txt` with duplicates removed, and say how many lines were removed.

```
before: 13 lines
after:  8 lines
removed 5 duplicate lines
```

**You already know:** `read`, `lines`, `unique`, `write`, `join`.
**Nudge:** `unique` keeps the first of each repeated line, in order. To rebuild
the file you need the lines back into one piece of text — `join` with a newline
as the glue: `join(clean, "\n")`.
**Careful:** write to a **new** file. Never overwrite the input until the output
looks right.
**Stretch:** make it work on any file named in `args |> first`.

---

## 4. The error hunt (medium)

**Job:** `app.log` is a fake server log. Say how many lines contain `ERROR`, and
print each one with a number in front.

```
3 errors found

1. 2026-11-01 09:14:22 ERROR disk full
2. ...
```

**You already know:** `read`, `lines`, `filter`, `contains`, `length`, `for`,
`say`, `text`.
**Nudge:** filter first, then count, then a `for` loop. The counter is a box you
add 1 to inside the loop (`n = n + 1`) — lesson 6 did exactly this.
**Stretch:** also count `WARNING` lines, and say which kind is more common.

---

## 5. Sort my folder (medium)

**Job:** take every file in `learn\challenges\junk\` and move it into a
sub-folder named after its extension: `txt\`, `jpg\`, `pdf\`. Files with no
extension go to `other\`.

**You already know:** `files`, `ext`, `mkdir`, `move`, `path`, `for`, `if`.
**Nudge:** `ext` returns the extension without a dot, and `""` when there isn't
one. `["txt", "jpg", "pdf"] |> contains(e)` tells you whether to trust it.
**Do it in two passes, like `examples/tidy.bolo`:** first a version that only
`say`s what it *would* move, and run it until the plan looks right. Then add the
`move`.
**Careful:** run it twice. The second run should find nothing to do, not crash.
That's the difference between a script and a script you trust.

---

## 6. Back up my own code (hard)

**Job:** copy every `.bolo` file in the whole project into
`learn\challenges\backup\`, keeping only the file name (not the folders). Say
how many were copied, and skip any that are already there and unchanged.

```
backup: 12 files copied, 3 already there
```

**You already know:** `walk`, `ext`, `name`, `mkdir`, `copy`, `exists`, `for`,
`if`, `say`, `text`.
**Nudge:** `walk(".")` lists everything below the current folder, recursively.
Filter to `.bolo`, then loop. To decide "already there", `exists` on the
destination path is enough for a first version — comparing contents is a
**stretch** goal (hint: `read` both and compare with `is`).
**Careful:** `backup\` is inside the folder you are walking. Your own copies
must not be mistaken for sources — `filter` on extension handles it, but think
about why that matters.
**Why it's hard:** paths. `copy(source, path("learn\\challenges\\backup", name(source)))`
is the whole trick, and the destination folder must exist first.

---

## When all six are done

You will have written: a text analyser, a de-duplicator, a log scanner, a file
sorter, and a backup tool. That is genuinely a useful toolbox, in a language you
learned this week.

Two honest gaps you will have felt by then:

- **No `while` loop.** Retrying something until it works is awkward with only
  `for` and recursion.
- **No dictionaries.** Counting *how many of each* thing (word frequencies, file
  types) needs a clunky `unique` + `filter` dance.

Both are on the list. Say the word and I will add them, with lessons to match.
