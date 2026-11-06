#!/usr/bin/env python3
"""Bolo 1.0 - a small, friendly language for everyday file, text and app chores.

New to programming? Start with learn/README.md - eight short lessons, no
experience assumed. Everything below is the reference, not the tutorial.

Why it exists: a one-off chore ("rename these photos", "count the words") costs
about 30 lines of Python boilerplate or an unreadable bash one-liner. In Bolo
a chore is a pipeline:

    files("photos") |> filter({ ext(it) is "jpg" }) |> each({ say(name(it)) })

Every builtin takes the thing it works on as its first argument, so `|>` is
just "put this value here":

    value |> f(a)          is the same as          f(value, a)

Language quick tour
-------------------
    say("hello")                 show something on the screen
    x = 3 * 4                    variables
    "a b" |> words |> length     pipelines ("then")
    { it * 2 }                   lambda, `it` is the argument
    { a, b -> a + b }            lambda with named parameters
    if x is 10 { } else { }      choices (`is` is `==`)
    for f in files(".") { }      loops over a list, text or table
    while n < 10 { n = n + 1 }   repeat while a question stays true
    break  /  continue           leave a loop / skip to the next step
    try { } catch problem { }    handle a problem; fail("...") raises one
    t = table("name", "Mari")    a table: values kept under names
    t["age"] = 12                read and write with [ ]
    for k, v in pairs(t) { }     walk a table
    if "a" in ["a", "b"] { }     membership (`not in` too)
    "Hi {name}, {2 + 3}"         put values inside text
    use "tools.bolo"             run another file once
    to double(n) { n * 2 }       functions (last value is returned)
    return 1                     ...or return explicitly
    nothing                      "no value at all" (also spelled nil)
    # comment                    comments run to the end of the line

    text(12)                     "12"      (also spelled str)
    number("12")                 12        (also spelled num)
    length([1, 2, 3])            3         (also spelled count)
    average([2, 4, 6])           4         (also spelled mean)

Run a file:       python bolo.py script.bolo [args...]
Run one line:     python bolo.py -e '1 + 2 |> say'
Type code live:   python bolo.py
"""

from __future__ import annotations

import difflib
import fnmatch
import functools
import json as jsonlib
import math
import os
import random as randomlib
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = "1.0"

__all__ = [
    "BoloError", "parse", "Interp", "run_source", "run_file",
    "format_error", "BUILTINS",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BoloError(Exception):
    """A Bolo problem, explained in plain words.

    `line` and `col` point at the source, `hint` is an optional nudge for
    beginners ("did you mean ...?"), and `file`/`source` name the file the
    problem really happened in, when that is not the program being run
    (a file pulled in with `use`).
    """

    def __init__(self, message: str, line: int | None = None,
                 col: int | None = None, hint: str | None = None,
                 file: str | None = None, source: str | None = None):
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.file = file
        self.source = source
        super().__init__(message)

    def __str__(self) -> str:
        where = f"line {self.line}: " if self.line else ""
        text = where + self.message
        if self.hint:
            text += f"\n  hint: {self.hint}"
        return text


def format_error(source: str, label: str, err: BoloError) -> str:
    """Turn an error plus its source into something a beginner can read.

    When the problem happened inside a file that was pulled in with `use`,
    the error carries that file's name and text, so the caret lands on the
    line that really failed instead of pointing at innocent code in the
    program that used it.
    """
    if err.source is not None:
        source = err.source
    if err.file:
        label = err.file
    out = [f"bolo: {label}" + (f": line {err.line}" if err.line else "")]
    if err.line:
        lines = source.splitlines()
        if 1 <= err.line <= len(lines):
            text = lines[err.line - 1]
            gutter = " " * len(str(err.line))
            out.append(f"  {err.line} | {text}")
            if err.col and err.col > 0:
                out.append(f"  {gutter} | " + " " * (err.col - 1) + "^")
    out.append("  " + err.message)
    if err.hint:
        out.append("  hint: " + err.hint)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

KEYWORDS = {
    "to", "if", "else", "for", "in", "return",
    "and", "or", "not", "is", "true", "false", "nil", "nothing",
    "while", "break", "continue", "try", "catch", "use",
}
TWO_CHAR_OPS = {"|>", "==", "!=", "<=", ">=", "->"}
ONE_CHAR_OPS = set("+-*/%<>=()[]{},;")

# The only escapes a backslash introduces inside text. Any other backslash
# stays where it is, so a regex like "\d+" or a Windows path like
# "C:\Users\me" arrives exactly as it was typed instead of losing its
# backslashes (which used to turn "\d+" into "d+" and "C:\Users" into
# "C:Users").
ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'",
}


@dataclass
class Token:
    kind: str          # num | str | name | kw | op | nl | eof
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"Token({self.kind}, {self.value!r}, {self.line})"


def tokenize(source: str) -> list[Token]:
    # Files saved by some Windows editors start with a byte-order mark.
    if source.startswith("\ufeff"):
        source = source[1:]

    tokens: list[Token] = []
    i, n = 0, len(source)

    def line_col(idx: int) -> tuple[int, int]:
        line = source.count("\n", 0, idx) + 1
        col = idx - source.rfind("\n", 0, idx)
        return line, col

    while i < n:
        ch = source[i]

        if ch in " \t\r":
            i += 1
            continue

        if ch == "\n":
            tokens.append(Token("nl", "\n", *line_col(i)))
            i += 1
            continue

        if ch == "#":
            end = source.find("\n", i)
            i = n if end < 0 else end
            continue

        line, col = line_col(i)

        if ch.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            is_float = False
            if j + 1 < n and source[j] == "." and source[j + 1].isdigit():
                is_float = True
                j += 1
                while j < n and source[j].isdigit():
                    j += 1
            text = source[i:j]
            tokens.append(Token("num", float(text) if is_float else int(text), line, col))
            i = j
            continue

        if ch in "\"'":
            quote, j, buf = ch, i + 1, []
            while j < n and source[j] != quote:
                if source[j] == "\n":
                    raise BoloError("unterminated string", line)
                if source[j] == "\\" and j + 1 < n:
                    esc = source[j + 1]
                    if esc in ESCAPES:
                        buf.append(ESCAPES[esc])
                        j += 2
                        continue
                    # Not an escape, just a backslash the person meant to
                    # keep: "\d+" is a regex and "C:\Users" is a path.
                    buf.append("\\")
                    j += 1
                    continue
                buf.append(source[j])
                j += 1
            if j >= n:
                raise BoloError("unterminated string", line)
            tokens.append(Token("str", "".join(buf), line, col))
            i = j + 1
            continue

        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            kind = "kw" if word in KEYWORDS else "name"
            tokens.append(Token(kind, word, line, col))
            i = j
            continue

        pair = source[i:i + 2]
        if pair in TWO_CHAR_OPS:
            tokens.append(Token("op", pair, line, col))
            i += 2
            continue

        if ch in ONE_CHAR_OPS:
            tokens.append(Token("op", ch, line, col))
            i += 1
            continue

        raise BoloError(f"unexpected character {ch!r}", line)

    tokens.append(Token("eof", None, *line_col(n)))
    return tokens


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

@dataclass
class Num:
    value: float


@dataclass
class Str:
    value: str


@dataclass
class Bool:
    value: bool


@dataclass
class Nil:
    pass


@dataclass
class Var:
    name: str
    line: int = 0
    col: int = 0


@dataclass
class ListLit:
    items: list


@dataclass
class Lambda:
    params: list
    body: list
    line: int = 0
    col: int = 0


@dataclass
class Call:
    fn: Any
    args: list
    line: int = 0
    col: int = 0


@dataclass
class Index:
    obj: Any
    index: Any
    line: int = 0
    col: int = 0


@dataclass
class Unary:
    op: str
    operand: Any
    line: int = 0
    col: int = 0


@dataclass
class Binary:
    op: str
    left: Any
    right: Any
    line: int = 0
    col: int = 0


@dataclass
class If:
    cond: Any
    then: list
    otherwise: list | None
    line: int = 0
    col: int = 0


@dataclass
class Assign:
    name: str
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class ExprStmt:
    expr: Any
    line: int = 0
    col: int = 0


@dataclass
class For:
    names: list
    iterable: Any
    body: list
    line: int = 0
    col: int = 0


@dataclass
class While:
    cond: Any
    body: list
    line: int = 0
    col: int = 0


@dataclass
class Break:
    line: int = 0
    col: int = 0


@dataclass
class Continue:
    line: int = 0
    col: int = 0


@dataclass
class Try:
    body: list
    name: str | None
    handler: list
    line: int = 0
    col: int = 0


@dataclass
class Use:
    path: str
    line: int = 0
    col: int = 0


@dataclass
class SetIndex:
    target: Any
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class FuncDef:
    name: str
    params: list
    body: list
    line: int = 0
    col: int = 0


@dataclass
class Return:
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class Program:
    stmts: list


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Higher binds tighter. `|>` sits above comparisons so that
# `x |> count > 5` means `(x |> count) > 5`, but below arithmetic so that
# `1 + 2 |> print` means `(1 + 2) |> print`.
PREC = {
    "or": 1,
    "and": 2,
    "==": 3, "!=": 3, "<": 3, "<=": 3, ">": 3, ">=": 3, "in": 3, "not in": 3,
    "|>": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "%": 6,
}
PREC_COMPARE = 3
PREC_MUL = 6


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    # -- token helpers ------------------------------------------------------
    def peek(self, k: int = 0) -> Token:
        j = self.i + k
        return self.tokens[j] if j < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        tok = self.peek()
        self.i += 1
        return tok

    def at_op(self, value: str | None = None) -> bool:
        tok = self.peek()
        return tok.kind == "op" and (value is None or tok.value == value)

    def at_kw(self, value: str | None = None) -> bool:
        tok = self.peek()
        return tok.kind == "kw" and (value is None or tok.value == value)

    def at_nl(self) -> bool:
        return self.peek().kind == "nl"

    def eof(self) -> bool:
        return self.peek().kind == "eof"

    def accept_op(self, value: str) -> Token | None:
        if self.at_op(value):
            return self.advance()
        return None

    def skip_newlines(self) -> None:
        while self.at_nl():
            self.advance()

    def skip_separators(self) -> None:
        while self.at_nl() or self.at_op(";"):
            self.advance()

    def skip_continuation_newlines(self) -> None:
        """Skip line breaks only when the next real token continues an expression.

        This is what makes a pipeline readable across lines:

            files("photos")
              |> filter({ ... })
              |> count
        """
        k = 0
        while self.peek(k).kind == "nl":
            k += 1
        tok = self.peek(k)
        continues = (
            (tok.kind == "op" and tok.value in PREC)
            or (tok.kind == "kw" and tok.value in ("and", "or", "is"))
        )
        if continues:
            self.skip_newlines()

    def describe(self, tok: Token | None = None) -> str:
        tok = tok or self.peek()
        if tok.kind == "eof":
            return "the end of the file"
        if tok.kind == "nl":
            return "the end of the line"
        if tok.kind == "str":
            return "some text"
        return f"'{tok.value}'"

    def expect_op(self, value: str) -> Token:
        tok = self.peek()
        if tok.kind == "op" and tok.value == value:
            return self.advance()
        raise BoloError(
            f"expected '{value}' but found {self.describe(tok)}", tok.line, tok.col
        )

    def expect_kw(self, value: str) -> Token:
        tok = self.peek()
        if tok.kind == "kw" and tok.value == value:
            return self.advance()
        raise BoloError(
            f"expected '{value}' but found {self.describe(tok)}", tok.line, tok.col
        )

    def expect_name(self, what: str = "a name") -> Token:
        tok = self.peek()
        if tok.kind == "name":
            return self.advance()
        raise BoloError(
            f"expected {what} but found {self.describe(tok)}", tok.line, tok.col
        )

    # -- program ------------------------------------------------------------
    def parse_program(self) -> Program:
        stmts: list = []
        while True:
            self.skip_separators()
            if self.eof():
                break
            stmts.append(self.parse_statement())
            if not (self.at_nl() or self.at_op(";") or self.at_op("}") or self.eof()):
                tok = self.peek()
                raise BoloError(
                    f"expected a new line or ';' but found {self.describe(tok)}",
                    tok.line, tok.col,
                    "each statement goes on its own line",
                )
        return Program(stmts)

    def parse_statement(self):
        tok = self.peek()

        if tok.kind == "kw":
            word = tok.value
            if word == "to":
                return self.parse_funcdef()
            if word == "for":
                return self.parse_for()
            if word == "while":
                return self.parse_while()
            if word == "try":
                return self.parse_try()
            if word == "use":
                return self.parse_use()
            if word in ("break", "continue"):
                start = self.advance()
                node = Break if word == "break" else Continue
                return node(start.line, start.col)
            if word == "return":
                start = self.advance()
                if self.at_nl() or self.at_op(";") or self.at_op("}") or self.eof():
                    return Return(None, start.line, start.col)
                return Return(self.parse_expr(), start.line, start.col)
            if word == "if":
                return ExprStmt(self.parse_if(), tok.line, tok.col)
            if word in ("and", "or", "else", "in", "is", "catch"):
                raise BoloError(f"unexpected '{word}'", tok.line, tok.col)

        if tok.kind == "op" and tok.value == "=":
            raise BoloError(
                "'=' gives a value to a name, but there is no name here",
                tok.line, tok.col,
                "write it like:  score = 10",
            )

        if tok.kind == "name" and self.looks_like_assign():
            start = self.advance()
            name = tok.value
            if self.at_op("["):
                target = Var(name, start.line, start.col)
                while self.at_op("["):
                    opening = self.advance()
                    self.skip_newlines()
                    index = self.parse_expr()
                    self.skip_newlines()
                    self.expect_op("]")
                    target = Index(target, index, opening.line, opening.col)
                self.expect_op("=")
                self.skip_newlines()
                return SetIndex(target, self.parse_expr(), start.line, start.col)
            self.advance()  # '='
            self.skip_newlines()
            return Assign(name, self.parse_expr(), start.line, start.col)

        return ExprStmt(self.parse_expr(), tok.line, tok.col)

    def looks_like_assign(self) -> bool:
        """True for `name = ...` and `name[...] = ...`, without consuming."""
        k = 1
        tok = self.peek(k)
        if tok.kind == "op" and tok.value == "=":
            return True
        if not (tok.kind == "op" and tok.value == "["):
            return False
        while self.peek(k).kind == "op" and self.peek(k).value == "[":
            depth = 0
            while True:
                tok = self.peek(k)
                if tok.kind == "eof":
                    return False
                if tok.kind == "op" and tok.value == "[":
                    depth += 1
                elif tok.kind == "op" and tok.value == "]":
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
                k += 1
        tok = self.peek(k)
        return tok.kind == "op" and tok.value == "="

    def parse_funcdef(self) -> FuncDef:
        start = self.expect_kw("to")
        name = self.expect_name("a function name").value
        self.expect_op("(")
        params: list[str] = []
        self.skip_newlines()
        if not self.at_op(")"):
            params.append(self.expect_name("a parameter name").value)
            while self.accept_op(","):
                self.skip_newlines()
                if self.at_op(")"):
                    break
                params.append(self.expect_name("a parameter name").value)
        self.skip_newlines()
        self.expect_op(")")
        self.skip_newlines()
        body = self.parse_block()
        return FuncDef(name, params, body, start.line, start.col)

    def parse_for(self) -> For:
        start = self.expect_kw("for")
        names = [self.expect_name("a loop name").value]
        while self.accept_op(","):
            self.skip_newlines()
            names.append(self.expect_name("a loop name").value)
        if not self.at_kw("in"):
            tok = self.peek()
            raise BoloError(
                f"expected 'in' but found {self.describe(tok)}", tok.line, tok.col,
                "write it like:  for fruit in fruits { ... }",
            )
        self.advance()
        self.skip_newlines()
        iterable = self.parse_expr()
        self.skip_newlines()
        body = self.parse_block()
        return For(names, iterable, body, start.line, start.col)

    def parse_while(self) -> While:
        start = self.expect_kw("while")
        self.skip_newlines()
        cond = self.parse_expr()
        self.skip_newlines()
        body = self.parse_block()
        return While(cond, body, start.line, start.col)

    def parse_try(self) -> Try:
        start = self.expect_kw("try")
        self.skip_newlines()
        body = self.parse_block()

        # `catch` may start on the next line.
        k = 0
        while self.peek(k).kind == "nl":
            k += 1
        if not (self.peek(k).kind == "kw" and self.peek(k).value == "catch"):
            tok = self.peek(k)
            raise BoloError(
                f"expected 'catch' but found {self.describe(tok)}",
                start.line, start.col,
                "write:  try { ... } catch problem { say(problem) }",
            )
        self.i += k
        self.advance()  # catch

        name = None
        if self.peek().kind == "name":
            name = self.advance().value
        self.skip_newlines()
        handler = self.parse_block()
        return Try(body, name, handler, start.line, start.col)

    def parse_use(self) -> Use:
        start = self.expect_kw("use")
        tok = self.peek()
        if tok.kind == "str":
            self.advance()
            path = tok.value
        elif tok.kind == "name":
            self.advance()
            path = tok.value + ".bolo"
        else:
            raise BoloError(
                "use needs a file name",
                tok.line, tok.col,
                'write it like:  use "tools.bolo"   or   use tools',
            )
        return Use(path, start.line, start.col)

    def parse_if(self) -> If:
        start = self.expect_kw("if")
        self.skip_newlines()
        cond = self.parse_expr()
        if self.at_op("="):
            tok = self.peek()
            raise BoloError(
                "use 'is' to compare, not '='", tok.line, tok.col,
                "'=' puts a value in a name; 'is' asks whether two things are equal",
            )
        self.skip_newlines()
        then = self.parse_block()
        otherwise = None

        # `else` may start on the next line, but a plain newline must stay
        # put so the statement/block terminator rules still see it.
        k = 0
        while self.peek(k).kind == "nl":
            k += 1
        if self.peek(k).kind == "kw" and self.peek(k).value == "else":
            self.i += k
            self.advance()
            self.skip_newlines()
            if self.at_kw("if"):
                tok = self.peek()
                otherwise = [ExprStmt(self.parse_if(), tok.line, tok.col)]
            else:
                otherwise = self.parse_block()
        return If(cond, then, otherwise, start.line, start.col)

    def parse_block(self) -> list:
        opening = self.expect_op("{")
        stmts: list = []
        while True:
            self.skip_separators()
            if self.at_op("}"):
                break
            if self.eof():
                raise BoloError(
                    "this '{' is never closed",
                    opening.line, opening.col,
                    "add a '}' to finish the block",
                )
            stmts.append(self.parse_statement())
            if not (self.at_nl() or self.at_op(";") or self.at_op("}") or self.eof()):
                tok = self.peek()
                raise BoloError(
                    f"expected a new line or ';' but found {self.describe(tok)}",
                    tok.line, tok.col,
                    "each statement goes on its own line",
                )
        self.expect_op("}")
        return stmts

    # -- expressions --------------------------------------------------------
    def parse_expr(self, min_prec: int = 1):
        left = self.parse_prefix()
        while True:
            self.skip_continuation_newlines()
            tok = self.peek()

            op = None
            prec = None
            if tok.kind == "op" and tok.value in PREC:
                op, prec = tok.value, PREC[tok.value]
            elif tok.kind == "kw" and tok.value in ("and", "or", "in"):
                op, prec = tok.value, PREC[tok.value]
            elif (
                tok.kind == "kw" and tok.value == "not"
                and self.peek(1).kind == "kw" and self.peek(1).value == "in"
            ):
                op, prec = "not in", PREC["in"]
            elif tok.kind == "kw" and tok.value == "is":
                op, prec = "is", PREC["=="]

            if op is None or prec < min_prec:
                break

            op_tok = self.advance()
            if op == "not in":
                self.advance()  # 'in'
            if op == "is":
                # `a is b` and `a is not b` read like English.
                if self.at_kw("not"):
                    self.advance()
                    op = "!="
                else:
                    op = "=="
            self.skip_newlines()
            right = self.parse_expr(prec + 1)

            if op == "|>":
                # `a |> f(b)` becomes `f(a, b)`.
                if isinstance(right, Call):
                    left = Call(right.fn, [left] + right.args, right.line, right.col)
                else:
                    left = Call(right, [left], op_tok.line, op_tok.col)
            else:
                left = Binary(op, left, right, op_tok.line, op_tok.col)
        return left

    def parse_prefix(self):
        tok = self.peek()
        if tok.kind == "kw" and tok.value == "not":
            self.advance()
            return Unary("not", self.parse_expr(PREC_COMPARE), tok.line, tok.col)
        if tok.kind == "op" and tok.value == "-":
            self.advance()
            return Unary("-", self.parse_expr(PREC_MUL + 1), tok.line, tok.col)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.at_op("("):
                opening = self.advance()
                args: list = []
                self.skip_newlines()
                if not self.at_op(")"):
                    args.append(self.parse_expr())
                    while self.accept_op(","):
                        self.skip_newlines()
                        if self.at_op(")"):
                            break
                        args.append(self.parse_expr())
                self.skip_newlines()
                self.expect_op(")")
                node = Call(node, args, opening.line, opening.col)
            elif self.at_op("["):
                opening = self.advance()
                self.skip_newlines()
                index = self.parse_expr()
                self.skip_newlines()
                self.expect_op("]")
                node = Index(node, index, opening.line, opening.col)
            else:
                return node

    def parse_primary(self):
        tok = self.peek()

        if tok.kind == "num":
            self.advance()
            return Num(tok.value)
        if tok.kind == "str":
            self.advance()
            return Str(tok.value)
        if tok.kind == "name":
            self.advance()
            return Var(tok.value, tok.line, tok.col)
        if tok.kind == "kw":
            if tok.value == "true":
                self.advance()
                return Bool(True)
            if tok.value == "false":
                self.advance()
                return Bool(False)
            if tok.value in ("nil", "nothing"):
                self.advance()
                return Nil()
            if tok.value == "if":
                return self.parse_if()
            raise BoloError(f"unexpected '{tok.value}'", tok.line, tok.col)

        if self.at_op("("):
            self.advance()
            self.skip_newlines()
            inner = self.parse_expr()
            self.skip_newlines()
            self.expect_op(")")
            return inner

        if self.at_op("["):
            self.advance()
            items: list = []
            self.skip_newlines()
            if not self.at_op("]"):
                items.append(self.parse_expr())
                while self.accept_op(","):
                    self.skip_newlines()
                    if self.at_op("]"):
                        break
                    items.append(self.parse_expr())
            self.skip_newlines()
            self.expect_op("]")
            return ListLit(items)

        if self.at_op("{"):
            return self.parse_lambda()

        raise BoloError(
            f"expected a value but found {self.describe(tok)}", tok.line, tok.col,
            "a value can be a number, some text in quotes, a name, a list, or a function",
        )

    def parse_lambda(self) -> Lambda:
        start = self.i
        opening = self.expect_op("{")

        # Two shapes: `{ it * 2 }` and `{ a, b -> a + b }`.
        if self.peek().kind == "name":
            names = [self.advance().value]
            while self.at_op(","):
                self.advance()
                if self.peek().kind != "name":
                    break
                names.append(self.advance().value)
            if self.at_op("->"):
                self.advance()
                body = self.parse_lambda_body()
                return Lambda(names, body, opening.line, opening.col)

        self.i = start
        self.expect_op("{")
        return Lambda(["it"], self.parse_lambda_body(), opening.line, opening.col)

    def parse_lambda_body(self) -> list:
        stmts: list = []
        while True:
            self.skip_separators()
            if self.at_op("}"):
                break
            if self.eof():
                raise BoloError(
                    "this '{' is never closed", self.peek().line, self.peek().col,
                    "add a '}' to finish it",
                )
            stmts.append(self.parse_statement())
            if not (self.at_nl() or self.at_op(";") or self.at_op("}") or self.eof()):
                tok = self.peek()
                raise BoloError(
                    f"expected a new line or ';' but found {self.describe(tok)}",
                    tok.line, tok.col,
                    "each statement goes on its own line",
                )
        self.expect_op("}")
        return stmts


def parse(source: str) -> Program:
    return Parser(tokenize(source)).parse_program()


@functools.lru_cache(maxsize=256)
def _parse_cached(source: str) -> Program:
    """Parse the small expression inside a `{...}` in text, once."""
    return parse(source)


# ---------------------------------------------------------------------------
# Runtime values and helpers
# ---------------------------------------------------------------------------

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    """`break` wants the nearest loop to stop."""


class ContinueSignal(Exception):
    """`continue` wants the nearest loop to start its next step."""


class QuitSignal(Exception):
    """`quit(code)` ends the program on purpose."""

    def __init__(self, code: int = 0):
        self.code = code


class Table:
    """A beginner-friendly dictionary: named values kept together."""

    __bolo_type__ = "table"

    def __init__(self) -> None:
        self.data: dict[Any, Any] = {}

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"Table({self.data!r})"


class Env:
    def __init__(self, parent: "Env | None" = None):
        self.vars: dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str, line: int | None = None, col: int | None = None):
        env: Env | None = self
        known: dict[str, Any] = {}
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            known.update(env.vars)
            env = env.parent

        hint = None
        close = difflib.get_close_matches(name, list(known), n=1, cutoff=0.6)
        if close:
            hint = f"did you mean '{close[0]}'? Names are case-sensitive."
        elif known:
            hint = "a name only exists after you give it a value, like:  score = 10"
        raise BoloError(f"I don't know the name '{name}'", line, col, hint)

    def define(self, name: str, value) -> None:
        self.vars[name] = value


@dataclass
class UserFunction:
    name: str
    params: list[str]
    body: list
    env: Env
    # Where this function was written. Errors raised inside it belong to
    # that file, even when the call happens much later in another one.
    file: str | None = None
    source: str | None = None


@dataclass
class Builtin:
    name: str
    fn: Any


def type_name(value) -> str:
    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "list"
    if isinstance(value, (UserFunction, Builtin)) or callable(value):
        return "function"
    bolo_type = getattr(value, "__bolo_type__", None)
    if isinstance(bolo_type, str):
        return bolo_type
    return type(value).__name__


def describe_type(value) -> str:
    """A short phrase for error messages: 'a number', 'text', 'nothing'."""
    kind = type_name(value)
    if kind in ("text", "nothing"):
        return kind
    return ("an " if kind[0] in "aeiou" else "a ") + kind


def truthy(value) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, (str, list)):
        return len(value) > 0
    if isinstance(value, Table):
        return len(value.data) > 0
    return True


def repr_value(value) -> str:
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(repr_value(v) for v in value) + "]"
    if isinstance(value, Table):
        inner = ", ".join(
            f"{key_text(k)}: {repr_value(v)}" for k, v in value.data.items()
        )
        return "{" + inner + "}"
    return to_str(value)


def key_text(key) -> str:
    if isinstance(key, str) and key.replace("_", "").isalnum():
        return key
    return repr_value(key)


def to_str(value) -> str:
    if value is None:
        return "nothing"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(repr_value(v) for v in value) + "]"
    if isinstance(value, Table):
        return repr_value(value)
    if isinstance(value, UserFunction):
        return f"<to {value.name}>"
    if isinstance(value, Builtin):
        return f"<builtin {value.name}>"
    return str(value)


def equal(a, b) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, bool):
        return a is b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, Table) and isinstance(b, Table):
        if set(a.data) != set(b.data):
            return False
        return all(equal(a.data[k], b.data[k]) for k in a.data)
    return a == b


def looks_like_number(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        float(value.strip())
        return True
    except ValueError:
        return False


def binary_op(op: str, left, right):
    if op == "+":
        if isinstance(left, bool) or isinstance(right, bool):
            raise BoloError(
                "you can't add true/false values",
                hint="use and / or for true and false",
            )
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        hint = "you can add two numbers, two pieces of text, or two lists"
        if looks_like_number(left) or looks_like_number(right):
            hint = 'text that looks like a number is still text - try number("12") + 1'
        raise BoloError(
            f"you can't add {describe_type(left)} and {describe_type(right)}",
            hint=hint,
        )

    if op in ("-", "*", "/", "%"):
        for side in (left, right):
            if isinstance(side, bool) or not isinstance(side, (int, float)):
                hint = "mathematics only works with numbers"
                if looks_like_number(side):
                    hint = 'that is text, not a number - try number("12")'
                raise BoloError(
                    f"you can't use '{op}' on {describe_type(side)}", hint=hint
                )
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise BoloError(
                    "you can't divide by zero",
                    hint="dividing into 0 parts has no answer",
                )
            return left / right
        if right == 0:
            raise BoloError("you can't take a remainder of zero")
        return left % right

    if op in ("==", "!=", "<", "<=", ">", ">="):
        if op == "==":
            return equal(left, right)
        if op == "!=":
            return not equal(left, right)
        both_numbers = (
            isinstance(left, (int, float)) and not isinstance(left, bool)
            and isinstance(right, (int, float)) and not isinstance(right, bool)
        )
        both_strings = isinstance(left, str) and isinstance(right, str)
        if not (both_numbers or both_strings):
            raise BoloError(
                f"you can't compare {describe_type(left)} and {describe_type(right)}",
                hint="compare two numbers, or two pieces of text",
            )
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        return left >= right

    if op in ("in", "not in"):
        found = member_of(left, right)
        return found if op == "in" else not found

    raise BoloError(f"unknown operator '{op}'")


def member_of(needle, haystack) -> bool:
    """`needle in haystack` for text, lists and tables."""
    if isinstance(haystack, str):
        if not isinstance(needle, str):
            raise BoloError(
                f"you can only look for text inside text, not {describe_type(needle)}"
            )
        return needle in haystack
    if isinstance(haystack, list):
        return any(equal(needle, item) for item in haystack)
    if isinstance(haystack, Table):
        return needle in haystack.data
    raise BoloError(
        f"you can't look inside {describe_type(haystack)}",
        hint="'in' works with a list, some text, or a table",
    )


def index_value(obj, idx):
    if isinstance(obj, (list, str)):
        if isinstance(idx, bool) or not isinstance(idx, (int, float)):
            raise BoloError(
                f"the position inside [...] must be a number, not {describe_type(idx)}"
            )
        i = int(idx)
        if i < 0:
            i += len(obj)
        if not 0 <= i < len(obj):
            raise BoloError(
                f"there is no position {int(idx)} - the list has {len(obj)} item(s)",
                hint="counting starts at 0, so the first item is [0]",
            )
        return obj[i]
    if isinstance(obj, Table):
        if idx in obj.data:
            return obj.data[idx]
        raise BoloError(
            f"this table has no key {repr_value(idx)}",
            hint="use has(t, key) to check first, or get(t, key, fallback)",
        )
    raise BoloError(
        f"you can't use [...] on {describe_type(obj)}",
        hint="only lists, text and tables have positions",
    )


def assign_index(obj, idx, value):
    """Support `xs[0] = ...` and `t["key"] = ...`."""
    if isinstance(obj, list):
        if isinstance(idx, bool) or not isinstance(idx, (int, float)):
            raise BoloError(
                f"the position inside [...] must be a number, not {describe_type(idx)}"
            )
        i = int(idx)
        if i < 0:
            i += len(obj)
        if not 0 <= i < len(obj):
            raise BoloError(
                f"there is no position {int(idx)} - the list has {len(obj)} item(s)",
                hint="counting starts at 0, so the first item is [0]",
            )
        obj[i] = value
        return value
    if isinstance(obj, Table):
        check_key(idx)
        obj.data[idx] = value
        return value
    if isinstance(obj, str):
        raise BoloError(
            "text can't be changed in place",
            hint="build a new text instead, with replace() or +",
        )
    raise BoloError(
        f"you can't put something inside {describe_type(obj)}",
        hint="only lists and tables can be changed with [ ]",
    )


def check_key(key) -> None:
    if isinstance(key, bool) or not isinstance(key, (str, int, float)):
        raise BoloError(
            f"a table key must be text or a number, not {describe_type(key)}",
            hint='for example:  put(t, "name", "Mari")',
        )


# ---------------------------------------------------------------------------
# Builtins
# ---------------------------------------------------------------------------

BUILTINS: dict[str, Any] = {}


def builtin(name: str):
    def register(fn):
        BUILTINS[name] = fn
        return fn
    return register


def _check(args: list, lo: int, hi: int, name: str) -> None:
    if not lo <= len(args) <= hi:
        want = str(lo) if lo == hi else f"{lo} to {hi}"
        raise BoloError(f"{name} needs {want} value(s), but got {len(args)}")


def _list(value, name: str) -> list:
    if isinstance(value, list):
        return value
    raise BoloError(f"{name} needs a list, got {describe_type(value)}")


def _str(value, name: str) -> str:
    if isinstance(value, str):
        return value
    raise BoloError(f"{name} needs text, got {describe_type(value)}")


def _num(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BoloError(f"{name} needs a number, got {type_name(value)}")
    return value


def _fn(value, name: str):
    if isinstance(value, (UserFunction, Builtin)) or callable(value):
        return value
    raise BoloError(f"{name} needs a function, got {type_name(value)}")


def _int_arg(value, name: str) -> int:
    return int(_num(value, name))


# -- output -----------------------------------------------------------------

@builtin("print")
def _print(interp, args):
    """print(values...) - write values to the screen, space separated."""
    sys.stdout.write(" ".join(to_str(v) for v in args) + "\n")
    sys.stdout.flush()
    return None


# -- conversion -------------------------------------------------------------

@builtin("str")
def _str_builtin(interp, args):
    _check(args, 1, 1, "text")
    return to_str(args[0])


@builtin("num")
def _num_builtin(interp, args):
    _check(args, 1, 1, "number")
    value = args[0]
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            raise BoloError(
                f"can't read {value!r} as a number",
                hint="a number looks like 42 or 3.14, with no other words around it",
            ) from None
    raise BoloError(f"can't turn {describe_type(value)} into a number")


@builtin("int")
def _int_builtin(interp, args):
    _check(args, 1, 1, "int")
    value = args[0]
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            raise BoloError(
                f"can't turn {value!r} into a whole number",
                hint="whole numbers look like 42, with nothing after the dot",
            ) from None
    raise BoloError(f"can't turn {describe_type(value)} into a number")


@builtin("bool")
def _bool_builtin(interp, args):
    _check(args, 1, 1, "bool")
    return truthy(args[0])


@builtin("type")
def _type_builtin(interp, args):
    _check(args, 1, 1, "type")
    return type_name(args[0])


# -- text -------------------------------------------------------------------

@builtin("upper")
def _upper(interp, args):
    _check(args, 1, 1, "upper")
    return _str(args[0], "upper").upper()


@builtin("lower")
def _lower(interp, args):
    _check(args, 1, 1, "lower")
    return _str(args[0], "lower").lower()


@builtin("trim")
def _trim(interp, args):
    _check(args, 1, 1, "trim")
    return _str(args[0], "trim").strip()


@builtin("split")
def _split(interp, args):
    _check(args, 1, 2, "split")
    text = _str(args[0], "split")
    if len(args) == 2:
        return text.split(_str(args[1], "split"))
    return text.split()


@builtin("words")
def _words(interp, args):
    _check(args, 1, 1, "words")
    return _str(args[0], "words").split()


@builtin("lines")
def _lines(interp, args):
    _check(args, 1, 1, "lines")
    return _str(args[0], "lines").splitlines()


@builtin("replace")
def _replace(interp, args):
    _check(args, 3, 3, "replace")
    return _str(args[0], "replace").replace(
        _str(args[1], "replace"), _str(args[2], "replace")
    )


@builtin("starts")
def _starts(interp, args):
    _check(args, 2, 2, "starts")
    return _str(args[0], "starts").startswith(_str(args[1], "starts"))


@builtin("ends")
def _ends(interp, args):
    _check(args, 2, 2, "ends")
    return _str(args[0], "ends").endswith(_str(args[1], "ends"))


@builtin("contains")
def _contains(interp, args):
    _check(args, 2, 2, "contains")
    subject, needle = args
    if isinstance(subject, list):
        return any(equal(item, needle) for item in subject)
    return _str(needle, "contains") in _str(subject, "contains")


@builtin("test")
def _test(interp, args):
    """test(text, pattern) - true when the regular expression matches."""
    _check(args, 2, 2, "test")
    text = _str(args[0], "test")
    pattern = _str(args[1], "test")
    try:
        return re.search(pattern, text) is not None
    except re.error as exc:
        raise BoloError(f"test: bad pattern {pattern!r}: {exc}") from None


@builtin("find")
def _find(interp, args):
    """find(text, pattern) - every regular expression match, as a list."""
    _check(args, 2, 2, "find")
    text = _str(args[0], "find")
    pattern = _str(args[1], "find")
    try:
        return re.findall(pattern, text)
    except re.error as exc:
        raise BoloError(f"find: bad pattern {pattern!r}: {exc}") from None


# -- lists ------------------------------------------------------------------

@builtin("count")
def _count(interp, args):
    _check(args, 1, 1, "length")
    value = args[0]
    if isinstance(value, (list, str)):
        return len(value)
    if isinstance(value, Table):
        return len(value.data)
    raise BoloError(
        f"length needs a list, text or table, got {describe_type(value)}"
    )


@builtin("first")
def _first(interp, args):
    _check(args, 1, 1, "first")
    items = _list(args[0], "first")
    return items[0] if items else None


@builtin("last")
def _last(interp, args):
    _check(args, 1, 1, "last")
    items = _list(args[0], "last")
    return items[-1] if items else None


@builtin("take")
def _take(interp, args):
    _check(args, 2, 2, "take")
    n = _int_arg(args[1], "take")
    subject = args[0]
    if not isinstance(subject, (list, str)):
        raise BoloError(f"take needs a list or string, got {type_name(subject)}")
    return subject[:n]


@builtin("skip")
def _skip(interp, args):
    _check(args, 2, 2, "skip")
    n = _int_arg(args[1], "skip")
    subject = args[0]
    if not isinstance(subject, (list, str)):
        raise BoloError(f"skip needs a list or string, got {type_name(subject)}")
    return subject[n:]


def _one_kind(items: list, name: str) -> None:
    """Say no when a sort mixes numbers with text or true/false.

    `sort([true, 1])` used to work by accident (Python ranks true as 1), which
    quietly disagreed with the rest of the language: comparing a boolean with
    a number is an error everywhere else.
    """
    kinds = set()
    for item in items:
        if isinstance(item, bool):
            kinds.add("true/false")
        elif isinstance(item, (int, float)):
            kinds.add("numbers")
        elif isinstance(item, str):
            kinds.add("text")
        else:
            kinds.add(type_name(item))
    if len(kinds) > 1:
        raise BoloError(
            f"{name} can only sort one kind of value, but this list mixes "
            + " and ".join(sorted(kinds)),
            hint="use text(x) or number(x) so every value is the same kind",
        )


@builtin("sort")
def _sort(interp, args):
    _check(args, 1, 1, "sort")
    items = _list(args[0], "sort")
    _one_kind(items, "sort")
    try:
        return sorted(items)
    except TypeError:
        raise BoloError("sort: the list mixes types that cannot be compared") from None


@builtin("sortby")
def _sortby(interp, args):
    _check(args, 2, 2, "sortby")
    items = _list(args[0], "sortby")
    fn = _fn(args[1], "sortby")
    keys = [interp.call_value(fn, [item]) for item in items]
    _one_kind(keys, "sortby")
    pairs = list(zip(keys, items))
    try:
        pairs.sort(key=lambda pair: pair[0])
    except TypeError:
        raise BoloError("sortby: the keys cannot be compared") from None
    return [item for _, item in pairs]


@builtin("reverse")
def _reverse(interp, args):
    _check(args, 1, 1, "reverse")
    subject = args[0]
    if isinstance(subject, list):
        return list(reversed(subject))
    if isinstance(subject, str):
        return subject[::-1]
    raise BoloError(f"reverse needs a list or string, got {type_name(subject)}")


@builtin("unique")
def _unique(interp, args):
    _check(args, 1, 1, "unique")
    out: list = []
    for item in _list(args[0], "unique"):
        if not any(equal(item, seen) for seen in out):
            out.append(item)
    return out


@builtin("sum")
def _sum(interp, args):
    _check(args, 1, 1, "sum")
    total = 0
    for item in _list(args[0], "sum"):
        total += _num(item, "sum")
    return total


@builtin("join")
def _join(interp, args):
    _check(args, 1, 2, "join")
    items = _list(args[0], "join")
    glue = _str(args[1], "join") if len(args) == 2 else ""
    return glue.join(to_str(item) for item in items)


@builtin("push")
def _push(interp, args):
    _check(args, 2, 2, "push")
    return _list(args[0], "push") + [args[1]]


@builtin("map")
def _map(interp, args):
    _check(args, 2, 2, "map")
    items = _list(args[0], "map")
    fn = _fn(args[1], "map")
    return [interp.call_value(fn, [item]) for item in items]


@builtin("filter")
def _filter(interp, args):
    _check(args, 2, 2, "filter")
    items = _list(args[0], "filter")
    fn = _fn(args[1], "filter")
    return [item for item in items if truthy(interp.call_value(fn, [item]))]


@builtin("each")
def _each(interp, args):
    _check(args, 2, 2, "each")
    items = _list(args[0], "each")
    fn = _fn(args[1], "each")
    for item in items:
        interp.call_value(fn, [item])
    return items


@builtin("reduce")
def _reduce(interp, args):
    _check(args, 3, 3, "reduce")
    items = _list(args[0], "reduce")
    acc = args[1]
    fn = _fn(args[2], "reduce")
    for item in items:
        acc = interp.call_value(fn, [acc, item])
    return acc


@builtin("range")
def _range(interp, args):
    _check(args, 1, 2, "range")
    if len(args) == 1:
        start, stop = 0, _int_arg(args[0], "range")
    else:
        start, stop = _int_arg(args[0], "range"), _int_arg(args[1], "range")
    return list(range(start, stop))


# -- files and paths --------------------------------------------------------

@builtin("name")
def _name(interp, args):
    _check(args, 1, 1, "name")
    return os.path.basename(_str(args[0], "name"))


@builtin("stem")
def _stem(interp, args):
    _check(args, 1, 1, "stem")
    return os.path.splitext(os.path.basename(_str(args[0], "stem")))[0]


@builtin("ext")
def _ext(interp, args):
    """ext(path) - the extension without the dot: 'jpg'."""
    _check(args, 1, 1, "ext")
    return os.path.splitext(os.path.basename(_str(args[0], "ext")))[1].lstrip(".")


@builtin("path")
def _path(interp, args):
    _check(args, 1, 32, "path")
    return os.path.join(*(_str(a, "path") for a in args))


@builtin("parent")
def _parent(interp, args):
    _check(args, 1, 1, "parent")
    return os.path.dirname(_str(args[0], "parent"))


@builtin("files")
def _files(interp, args):
    """files(folder, pattern?) - files directly inside folder, sorted."""
    _check(args, 0, 2, "files")
    folder = _str(args[0], "files") if args else "."
    pattern = _str(args[1], "files") if len(args) == 2 else "*"
    if not os.path.isdir(folder):
        raise BoloError(f"files: not a folder: {folder}")
    out = []
    for entry in sorted(os.listdir(folder)):
        full = os.path.join(folder, entry)
        if os.path.isfile(full) and fnmatch.fnmatch(entry, pattern):
            out.append(full)
    return out


@builtin("walk")
def _walk(interp, args):
    """walk(folder, pattern?) - every file below folder, recursively."""
    _check(args, 0, 2, "walk")
    folder = _str(args[0], "walk") if args else "."
    pattern = _str(args[1], "walk") if len(args) == 2 else "*"
    if not os.path.isdir(folder):
        raise BoloError(f"walk: not a folder: {folder}")
    out = []
    for root, dirs, names in os.walk(folder):
        dirs.sort()
        for entry in sorted(names):
            if fnmatch.fnmatch(entry, pattern):
                out.append(os.path.join(root, entry))
    return out


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


@builtin("read")
def _read(interp, args):
    _check(args, 1, 1, "read")
    path = _str(args[0], "read")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError as exc:
        raise BoloError(f"read: {exc}") from None


@builtin("write")
def _write(interp, args):
    _check(args, 2, 2, "write")
    path = _str(args[0], "write")
    text = _str(args[1], "write")
    _ensure_parent(path)
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        raise BoloError(f"write: {exc}") from None
    return path


@builtin("append")
def _append(interp, args):
    _check(args, 2, 2, "append")
    path = _str(args[0], "append")
    text = _str(args[1], "append")
    _ensure_parent(path)
    try:
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        raise BoloError(f"append: {exc}") from None
    return path


@builtin("mkdir")
def _mkdir(interp, args):
    _check(args, 1, 1, "mkdir")
    path = _str(args[0], "mkdir")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        raise BoloError(f"mkdir: {exc}") from None
    return path


@builtin("move")
def _move(interp, args):
    _check(args, 2, 2, "move")
    source = _str(args[0], "move")
    target = _str(args[1], "move")
    _ensure_parent(target)
    try:
        shutil.move(source, target)
    except OSError as exc:
        raise BoloError(f"move: {exc}") from None
    return target


@builtin("copy")
def _copy(interp, args):
    _check(args, 2, 2, "copy")
    source = _str(args[0], "copy")
    target = _str(args[1], "copy")
    _ensure_parent(target)
    try:
        shutil.copy2(source, target)
    except OSError as exc:
        raise BoloError(f"copy: {exc}") from None
    return target


@builtin("delete")
def _delete(interp, args):
    _check(args, 1, 1, "delete")
    path = _str(args[0], "delete")
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        raise BoloError(f"delete: {exc}") from None
    return path


@builtin("exists")
def _exists(interp, args):
    _check(args, 1, 1, "exists")
    return os.path.exists(_str(args[0], "exists"))


@builtin("isfile")
def _isfile(interp, args):
    _check(args, 1, 1, "isfile")
    return os.path.isfile(_str(args[0], "isfile"))


@builtin("isdir")
def _isdir(interp, args):
    _check(args, 1, 1, "isdir")
    return os.path.isdir(_str(args[0], "isdir"))


@builtin("size")
def _size(interp, args):
    """size(p) - how many bytes a file holds."""
    _check(args, 1, 1, "size")
    path = _str(args[0], "size")
    if os.path.isdir(path):
        raise BoloError(
            f"size: {path} is a folder, and a folder has no single size",
            hint="add the files up:  files(path) |> map({ size(it) }) |> sum",
        )
    try:
        return os.path.getsize(path)
    except OSError as exc:
        raise BoloError(f"size: {exc}") from None


@builtin("modified")
def _modified(interp, args):
    """modified(p) - when the file last changed, like 2026-11-05 14:03:22."""
    _check(args, 1, 1, "modified")
    path = _str(args[0], "modified")
    try:
        stamp = os.path.getmtime(path)
    except OSError as exc:
        raise BoloError(f"modified: {exc}") from None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))


# -- numbers, time and chance ----------------------------------------------

def _numbers(items: list, name: str) -> list[float]:
    out = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise BoloError(
                f"{name} needs numbers, but found {describe_type(item)}",
                hint="text that looks like a number is still text - try number(x)",
            )
        out.append(item)
    return out


@builtin("round")
def _round(interp, args):
    """round(n, places?) - the nearest whole number (or nearest 0.1, 0.01...)."""
    _check(args, 1, 2, "round")
    value = _num(args[0], "round")
    places = _int_arg(args[1], "round") if len(args) > 1 else 0
    factor = 10 ** places
    scaled = value * factor
    answer = math.floor(scaled + 0.5) if scaled >= 0 else math.ceil(scaled - 0.5)
    answer = answer / factor
    return int(answer) if places <= 0 else answer


@builtin("floor")
def _floor(interp, args):
    """floor(n) - the nearest whole number below."""
    _check(args, 1, 1, "floor")
    return int(math.floor(_num(args[0], "floor")))


@builtin("ceil")
def _ceil(interp, args):
    """ceil(n) - the nearest whole number above."""
    _check(args, 1, 1, "ceil")
    return int(math.ceil(_num(args[0], "ceil")))


@builtin("abs")
def _abs(interp, args):
    """abs(n) - the distance from zero, always positive."""
    _check(args, 1, 1, "abs")
    return abs(_num(args[0], "abs"))


@builtin("sqrt")
def _sqrt(interp, args):
    """sqrt(n) - the number that, multiplied by itself, gives n."""
    _check(args, 1, 1, "sqrt")
    value = _num(args[0], "sqrt")
    if value < 0:
        raise BoloError(
            "you can't take the square root of a negative number",
            hint="try abs(n) first if you only care about the size",
        )
    return math.sqrt(value)


def _minmax(name: str, want_min: bool):
    @builtin(name)
    def _fn(interp, args):
        _check(args, 1, 999, name)
        items = args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
        if not items:
            raise BoloError(f"{name} needs at least one value")
        numeric = all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in items
        )
        textual = all(isinstance(v, str) for v in items)
        if not (numeric or textual):
            raise BoloError(
                f"{name} needs all numbers or all text, not a mix",
                hint="convert first with number(x) or text(x)",
            )
        best = items[0]
        for item in items[1:]:
            if (item < best) if want_min else (item > best):
                best = item
        return best
    return _fn


_minmax("min", True)
_minmax("max", False)


@builtin("average")
def _average(interp, args):
    """average(xs) - the sum divided by the count. Also spelled mean."""
    _check(args, 1, 1, "average")
    items = _numbers(_list(args[0], "average"), "average")
    if not items:
        raise BoloError("average needs at least one number, but the list is empty")
    return sum(items) / len(items)


@builtin("random")
def _random(interp, args):
    """random() - a decimal from 0 up to (not including) 1."""
    _check(args, 0, 0, "random")
    return randomlib.random()


@builtin("random_int")
def _random_int(interp, args):
    """random_int(a, b) - a whole number from a to b, both allowed."""
    _check(args, 2, 2, "random_int")
    low = _int_arg(args[0], "random_int")
    high = _int_arg(args[1], "random_int")
    if low > high:
        low, high = high, low
    return randomlib.randint(low, high)


@builtin("choose")
def _choose(interp, args):
    """choose(xs) - pick one item at random."""
    _check(args, 1, 1, "choose")
    items = _list(args[0], "choose")
    if not items:
        raise BoloError("choose needs at least one item, but the list is empty")
    return randomlib.choice(items)


@builtin("now")
def _now(interp, args):
    """now() - the date and time here, like 2026-11-05 14:03:22."""
    _check(args, 0, 0, "now")
    return time.strftime("%Y-%m-%d %H:%M:%S")


@builtin("today")
def _today(interp, args):
    """today() - just the date here, like 2026-11-05."""
    _check(args, 0, 0, "today")
    return time.strftime("%Y-%m-%d")


@builtin("sleep")
def _sleep(interp, args):
    """sleep(seconds) - wait, then carry on."""
    _check(args, 1, 1, "sleep")
    seconds = _num(args[0], "sleep")
    if seconds < 0:
        raise BoloError("sleep needs a number of seconds that is 0 or more")
    time.sleep(seconds)
    return None


# -- tables ----------------------------------------------------------------

def _table_arg(value, name: str) -> Table:
    if isinstance(value, Table):
        return value
    raise BoloError(f"{name} needs a table, got {describe_type(value)}")


@builtin("table")
def _table(interp, args):
    """table(...) - an empty table, or one built from key, value pairs."""
    result = Table()
    if len(args) == 1 and isinstance(args[0], Table):
        result.data.update(args[0].data)
        return result
    if len(args) % 2 != 0:
        raise BoloError(
            "table needs key, value pairs",
            hint='for example:  person = table("name", "Mari", "age", 12)',
        )
    for i in range(0, len(args), 2):
        check_key(args[i])
        result.data[args[i]] = args[i + 1]
    return result


@builtin("put")
def _put(interp, args):
    """put(t, key, value) - store or replace one value in a table."""
    _check(args, 3, 3, "put")
    table = _table_arg(args[0], "put")
    check_key(args[1])
    table.data[args[1]] = args[2]
    return table


@builtin("get")
def _get(interp, args):
    """get(t, key, fallback?) - read one value; fallback when it is missing."""
    _check(args, 2, 3, "get")
    table = _table_arg(args[0], "get")
    fallback = args[2] if len(args) > 2 else None
    return table.data.get(args[1], fallback)


@builtin("has")
def _has(interp, args):
    """has(t, key) - is this key in the table?"""
    _check(args, 2, 2, "has")
    return args[1] in _table_arg(args[0], "has").data


@builtin("remove")
def _remove(interp, args):
    """remove(t, key) - take one key out, if it is there."""
    _check(args, 2, 2, "remove")
    table = _table_arg(args[0], "remove")
    table.data.pop(args[1], None)
    return table


@builtin("keys")
def _keys(interp, args):
    """keys(t) - a list of all the names in a table."""
    _check(args, 1, 1, "keys")
    return list(_table_arg(args[0], "keys").data.keys())


@builtin("values")
def _values(interp, args):
    """values(t) - a list of all the values in a table."""
    _check(args, 1, 1, "values")
    return list(_table_arg(args[0], "values").data.values())


@builtin("pairs")
def _pairs(interp, args):
    """pairs(t) - [key, value] for each entry, for `for k, v in pairs(t)`."""
    _check(args, 1, 1, "pairs")
    return [[k, v] for k, v in _table_arg(args[0], "pairs").data.items()]


# -- more text and list helpers --------------------------------------------

@builtin("pad")
def _pad(interp, args):
    """pad(s, width) - add spaces on the right until it is wide enough."""
    _check(args, 2, 2, "pad")
    text = _str(args[0], "pad")
    width = _int_arg(args[1], "pad")
    return text.ljust(width)


@builtin("repeat")
def _repeat(interp, args):
    """repeat(x, times) - copy text or a list several times."""
    _check(args, 2, 2, "repeat")
    times = _int_arg(args[1], "repeat")
    if times < 0:
        times = 0
    value = args[0]
    if isinstance(value, str):
        return value * times
    if isinstance(value, list):
        return value * times
    raise BoloError(f"repeat needs text or a list, got {describe_type(value)}")


@builtin("index_of")
def _index_of(interp, args):
    """index_of(xs, x) - where it is, or -1 when it is not there."""
    _check(args, 2, 2, "index_of")
    haystack, needle = args
    if isinstance(haystack, str):
        return haystack.find(_str(needle, "index_of"))
    items = _list(haystack, "index_of")
    for i, item in enumerate(items):
        if equal(item, needle):
            return i
    return -1


@builtin("insert")
def _insert(interp, args):
    """insert(xs, i, x) - a copy with x added at position i."""
    _check(args, 3, 3, "insert")
    items = list(_list(args[0], "insert"))
    i = _int_arg(args[1], "insert")
    if i < 0:
        i += len(items)
    i = max(0, min(i, len(items)))
    items.insert(i, args[2])
    return items


@builtin("flatten")
def _flatten(interp, args):
    """flatten(xs) - one list holding the items of the lists inside."""
    _check(args, 1, 1, "flatten")
    out: list = []
    for item in _list(args[0], "flatten"):
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


@builtin("slice")
def _slice(interp, args):
    """slice(xs, from, to?) - part of a list or text, like Python slicing."""
    _check(args, 2, 3, "slice")
    value = args[0]
    if not isinstance(value, (list, str)):
        raise BoloError(f"slice needs a list or text, got {describe_type(value)}")
    start = _int_arg(args[1], "slice")
    if len(args) > 2:
        stop = _int_arg(args[2], "slice")
    else:
        stop = None
    return value[start:stop]


# -- data, people and control ----------------------------------------------

def _from_json(value):
    if isinstance(value, dict):
        table = Table()
        for key, item in value.items():
            table.data[key] = _from_json(item)
        return table
    if isinstance(value, list):
        return [_from_json(item) for item in value]
    return value


def _to_json(value):
    if isinstance(value, Table):
        return {str(key): _to_json(item) for key, item in value.data.items()}
    if isinstance(value, list):
        return [_to_json(item) for item in value]
    return value


@builtin("json")
def _json(interp, args):
    """json(text) - read JSON text into lists, tables, numbers and text."""
    _check(args, 1, 1, "json")
    text = _str(args[0], "json")
    try:
        return _from_json(jsonlib.loads(text))
    except jsonlib.JSONDecodeError as exc:
        raise BoloError(
            f"that is not valid JSON: {exc.msg} (column {exc.colno})",
            hint='example:  json("{\\"name\\": \\"Mari\\"}")',
        ) from None


@builtin("to_json")
def _to_json_builtin(interp, args):
    """to_json(x) - turn lists and tables into JSON text."""
    _check(args, 1, 1, "to_json")
    return jsonlib.dumps(_to_json(args[0]), ensure_ascii=False, indent=2)


@builtin("prompt")
def _prompt(interp, args):
    """prompt(text?) - ask the person at the keyboard for a line."""
    _check(args, 0, 1, "prompt")
    if args:
        sys.stdout.write(to_str(args[0]) + " ")
        sys.stdout.flush()
    try:
        return input()
    except (EOFError, KeyboardInterrupt):
        return None


@builtin("fail")
def _fail(interp, args):
    """fail(text) - stop with a problem that try/catch can catch."""
    _check(args, 0, 1, "fail")
    message = to_str(args[0]) if args else "something went wrong"
    raise BoloError(message)


@builtin("quit")
def _quit(interp, args):
    """quit(code?) - stop the program now. 0 means success."""
    _check(args, 0, 1, "quit")
    code = _int_arg(args[0], "quit") if args else 0
    raise QuitSignal(code)


# -- desktop apps -----------------------------------------------------------

def _gui_for(interp):
    """Create the GUI session on first use; importing tkinter only then."""
    gui = getattr(interp, "gui", None)
    if gui is None:
        from bolo_gui import Gui

        gui = Gui(interp)
        interp.gui = gui
    return gui


def _register_gui(name: str) -> None:
    def call(interp, args):
        return getattr(_gui_for(interp), name)(args)

    call.__name__ = f"_gui_{name}"
    BUILTINS[name] = call


for _gui_name in (
    "window", "row", "label", "heading", "button", "input", "textbox",
    "check", "value", "set", "on_click", "on_change", "add_line", "clear",
    "show", "alert", "ask", "choose_file", "save_file", "later", "every",
    "close",
):
    _register_gui(_gui_name)


# Friendly names for the words a beginner meets first. Both spellings work.
BUILTINS["say"] = BUILTINS["print"]
BUILTINS["length"] = BUILTINS["count"]
BUILTINS["text"] = BUILTINS["str"]
BUILTINS["number"] = BUILTINS["num"]
BUILTINS["mean"] = BUILTINS["average"]


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interp:
    def __init__(self):
        self.globals = Env()
        for name, fn in BUILTINS.items():
            self.globals.define(name, Builtin(name, fn))
        self.globals.define("args", [])
        self.base_dir = Path.cwd()
        self.loaded: set[str] = set()
        self.exit_code = 0
        # Which file is running right now, so an error can name it (and so a
        # function remembers the file it was written in).
        self.file_label: str | None = None
        self.source_text: str | None = None

    # -- statements ---------------------------------------------------------
    def run(self, program: Program):
        self.exit_code = 0
        try:
            result = self.exec_block(program.stmts, self.globals)
        except ReturnSignal as signal:
            result = signal.value
        except QuitSignal as signal:
            self.exit_code = signal.code
            result = None
        except (BreakSignal, ContinueSignal):
            raise BoloError(
                "'break' and 'continue' only work inside a loop",
                hint="put them inside for or while",
            ) from None
        gui = getattr(self, "gui", None)
        if gui is not None:
            gui.finish()
        return result

    def exec_block(self, stmts: list, env: Env):
        result = None
        for stmt in stmts:
            try:
                result = self.exec(stmt, env)
            except BoloError as err:
                if err.line is None:
                    err.line = getattr(stmt, "line", None)
                    err.col = getattr(stmt, "col", None)
                raise
        return result

    def exec(self, node, env: Env):
        if isinstance(node, ExprStmt):
            return self.eval(node.expr, env)
        if isinstance(node, Assign):
            value = self.eval(node.value, env)
            env.define(node.name, value)
            return value
        if isinstance(node, SetIndex):
            container = self.eval(node.target.obj, env)
            key = self.eval(node.target.index, env)
            value = self.eval(node.value, env)
            try:
                return assign_index(container, key, value)
            except BoloError as err:
                if err.line is None:
                    err.line, err.col = node.line, node.col
                raise
        if isinstance(node, FuncDef):
            fn = UserFunction(
                node.name, node.params, node.body, env,
                file=self.file_label, source=self.source_text,
            )
            env.define(node.name, fn)
            return fn
        if isinstance(node, For):
            items = self.eval(node.iterable, env)
            if isinstance(items, Table):
                items = [[k, v] for k, v in items.data.items()]
            if not isinstance(items, (list, str)):
                raise BoloError(
                    "for can only walk through a list, not " + describe_type(items),
                    node.line, node.col,
                    "put the values in a list, like:  for x in [1, 2, 3] { ... }",
                )
            result = None
            for item in items:
                if len(node.names) == 1:
                    env.define(node.names[0], item)
                else:
                    if not isinstance(item, list) or len(item) != len(node.names):
                        raise BoloError(
                            f"this loop asks for {len(node.names)} values at each "
                            f"step, but got {describe_type(item)}",
                            node.line, node.col,
                            "use pairs(t) to walk a table, or one name for a list",
                        )
                    for name, value in zip(node.names, item):
                        env.define(name, value)
                try:
                    result = self.exec_block(node.body, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return result
        if isinstance(node, While):
            result = None
            steps = 0
            while truthy(self.eval(node.cond, env)):
                steps += 1
                if steps > 5_000_000:
                    raise BoloError(
                        "this loop has run 5,000,000 times and has not stopped",
                        node.line, node.col,
                        "check that something inside the loop changes the condition",
                    )
                try:
                    result = self.exec_block(node.body, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return result
        if isinstance(node, Break):
            raise BreakSignal()
        if isinstance(node, Continue):
            raise ContinueSignal()
        if isinstance(node, Try):
            try:
                return self.exec_block(node.body, env)
            except BoloError as err:
                if node.name:
                    env.define(node.name, err.message)
                return self.exec_block(node.handler, env)
        if isinstance(node, Use):
            return self.use_file(node, env)
        if isinstance(node, Return):
            raise ReturnSignal(self.eval(node.value, env) if node.value else None)
        raise BoloError("cannot run this expression as a statement")

    def use_file(self, node: Use, env: Env):
        """`use "tools.bolo"` runs another file here, once."""
        path = Path(node.path)
        if not path.is_absolute():
            here = Path(getattr(self, "base_dir", Path.cwd()))
            path = here / path
        path = path.resolve()
        key = str(path)
        if key in self.loaded:
            return None
        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise BoloError(
                f"use can't open {node.path}: {exc}",
                node.line, node.col,
                "the file must sit next to the program that uses it",
            ) from None
        self.loaded.add(key)
        try:
            program = parse(source)
        except BoloError as err:
            raise BoloError(
                err.message, err.line, err.col, err.hint,
                file=path.name, source=source,
            ) from None
        previous = getattr(self, "base_dir", Path.cwd())
        previous_label = self.file_label
        previous_source = self.source_text
        self.base_dir = path.parent
        self.file_label = path.name
        self.source_text = source
        try:
            return self.exec_block(program.stmts, env)
        except BoloError as err:
            # Top-level code in a used file fails in that file. The first
            # stamp wins, so the innermost file keeps the blame.
            if err.file is None:
                err.file = path.name
                err.source = source
            raise
        finally:
            self.base_dir = previous
            self.file_label = previous_label
            self.source_text = previous_source

    # -- expressions --------------------------------------------------------
    def eval(self, node, env: Env):
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Str):
            return self.interpolate(node.value, env)
        if isinstance(node, Bool):
            return node.value
        if isinstance(node, Nil):
            return None
        if isinstance(node, Var):
            return env.get(node.name, node.line, node.col)
        if isinstance(node, ListLit):
            return [self.eval(item, env) for item in node.items]
        if isinstance(node, Lambda):
            return UserFunction(
                "<lambda>", node.params, node.body, env,
                file=self.file_label, source=self.source_text,
            )
        if isinstance(node, If):
            if truthy(self.eval(node.cond, env)):
                return self.exec_block(node.then, env)
            if node.otherwise is not None:
                return self.exec_block(node.otherwise, env)
            return None
        if isinstance(node, Call):
            fn = self.eval(node.fn, env)
            args = [self.eval(arg, env) for arg in node.args]
            return self.call_value(
                fn, args, node.line, node.col, self.shadow_hint(node.fn, fn)
            )
        if isinstance(node, Index):
            try:
                return index_value(self.eval(node.obj, env), self.eval(node.index, env))
            except BoloError as err:
                if err.line is None:
                    err.line, err.col = node.line, node.col
                raise
        if isinstance(node, Unary):
            value = self.eval(node.operand, env)
            if node.op == "not":
                return not truthy(value)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise BoloError(
                    f"you can't put '{node.op}' in front of {describe_type(value)}",
                    node.line, node.col,
                )
            return -value
        if isinstance(node, Binary):
            if node.op == "and":
                left = self.eval(node.left, env)
                return self.eval(node.right, env) if truthy(left) else left
            if node.op == "or":
                left = self.eval(node.left, env)
                return left if truthy(left) else self.eval(node.right, env)
            try:
                return binary_op(
                    node.op, self.eval(node.left, env), self.eval(node.right, env)
                )
            except BoloError as err:
                if err.line is None:
                    err.line, err.col = node.line, node.col
                raise
        raise BoloError("cannot evaluate this expression")

    # -- text with values inside --------------------------------------------
    def interpolate(self, text: str, env: Env) -> str:
        """Fill `{name}` holes in text. Write {{ or }} for a real brace."""
        if "{" not in text:
            return text
        out: list[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "{" and text.startswith("{{", i):
                out.append("{")
                i += 2
                continue
            if ch == "}" and text.startswith("}}", i):
                out.append("}")
                i += 2
                continue
            if ch != "{":
                out.append(ch)
                i += 1
                continue

            end = self._matching_brace(text, i)
            if end is None:
                # Not a value hole at all: keep the rest exactly as typed.
                out.append(text[i:])
                break
            source = text[i + 1:end].strip()
            if not source:
                # An empty pair is just text, so "use { }" still works.
                out.append("{")
                i += 1
                continue
            ok, value = self.eval_text_value(source, env)
            if not ok:
                # Not a value (JSON, maths notes, code samples): keep it as text.
                out.append(text[i:end + 1])
            else:
                out.append(to_str(value))
            i = end + 1
        return "".join(out)

    def _matching_brace(self, text: str, start: int) -> int | None:
        depth = 0
        quote = ""
        i = start
        while i < len(text):
            ch = text[i]
            if quote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = ""
            elif ch in "\"'":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return None

    def eval_text_value(self, source: str, env: Env):
        """Return (True, value) for a real value, or (False, None) for plain text."""
        try:
            program = _parse_cached(source)
        except BoloError:
            return False, None
        if len(program.stmts) != 1 or not isinstance(program.stmts[0], ExprStmt):
            return False, None
        return True, self.eval(program.stmts[0].expr, env)

    # -- calls --------------------------------------------------------------
    def shadow_hint(self, callee, fn) -> str | None:
        """Explain the case where a box hides a builtin, e.g. `text = "hi"`.

        Beginners naturally name a variable `text` or `length`, which silently
        replaces the builtin of the same name. Without this hint the error
        ("text is not a function") sends them looking in the wrong place.
        """
        if isinstance(fn, (Builtin, UserFunction)) or callable(fn):
            return None
        if isinstance(callee, Var) and callee.name in BUILTINS:
            return (
                f"there is a built-in called '{callee.name}', but you put a "
                f"different value in a box with that name. Rename the box."
            )
        return None

    def call_value(self, fn, args: list, line: int | None = None,
                   col: int | None = None, hint: str | None = None):
        if isinstance(fn, Builtin):
            try:
                return fn.fn(self, args)
            except (ReturnSignal, BreakSignal, ContinueSignal, QuitSignal):
                raise
            except BoloError as err:
                if err.line is None:
                    err.line, err.col = line, col
                raise
            except Exception as exc:                       # noqa: BLE001 - reported to user
                raise BoloError(f"{fn.name}: {exc}", line, col) from None

        if isinstance(fn, UserFunction):
            if len(args) != len(fn.params):
                if fn.name == "<lambda>":
                    subject = "this function"
                else:
                    subject = f"{fn.name}"
                raise BoloError(
                    f"{subject} needs {len(fn.params)} value(s) but got {len(args)}",
                    line, col,
                    "values go inside the parentheses, separated by commas",
                )
            local = Env(fn.env)
            for param, value in zip(fn.params, args):
                local.define(param, value)
            try:
                return self.exec_block(fn.body, local)
            except ReturnSignal as signal:
                return signal.value
            except BoloError as err:
                # A function written in another file fails in that file.
                if err.file is None and fn.file:
                    err.file = fn.file
                    err.source = fn.source
                raise

        raise BoloError(
            f"{describe_type(fn)} is not a function, so it can't be called",
            line, col,
            hint or "only functions can be followed by (...)",
        )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

REPL_HELP = """\
Type Bolo code and press Enter. Examples:

    say("hello")
    2 + 3
    [1, 2, 3] |> length
    help      show this text
    quit      leave
"""


def braces_open(source: str) -> bool:
    """True while a line has an unclosed {, so the prompt can wait for more."""
    depth = 0
    in_text = False
    quote = ""
    i = 0
    while i < len(source):
        ch = source[i]
        if in_text:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                in_text = False
        elif ch in "\"'":
            in_text, quote = True, ch
        elif ch == "#":
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return depth > 0


def repl() -> int:
    interp = Interp()
    print(f"Bolo {VERSION} - type code, press Enter. Type help or quit.")
    buffer = ""

    while True:
        prompt = "bolo> " if not buffer else "     ..> "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        stripped = line.strip()
        if not buffer and stripped in ("quit", "exit"):
            return 0
        if not buffer and stripped in ("help", "?"):
            print(REPL_HELP)
            continue
        if not buffer and not stripped:
            continue

        buffer += line + "\n"
        if braces_open(buffer):
            continue

        try:
            result = interp.run(parse(buffer))
            if result is not None:
                print(repr_value(result))
        except BoloError as err:
            print(format_error(buffer, "input", err), file=sys.stderr)

        buffer = ""


def run_source(source: str, argv: list[str] | None = None, base_dir=None,
               label: str | None = None):
    """Parse and run Bolo source. Returns the value of the last statement."""
    interp = Interp()
    if base_dir is not None:
        interp.base_dir = Path(base_dir)
    interp.file_label = label
    interp.source_text = source
    interp.globals.define("args", list(argv or []))
    return interp.run(parse(source))


def run_file(path: str, argv: list[str] | None = None):
    target = Path(path)
    with open(target, encoding="utf-8-sig") as handle:
        source = handle.read()
    return run_source(
        source, argv, base_dir=target.resolve().parent, label=target.name,
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        return repl()
    if args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if args[0] in ("-v", "--version"):
        print(f"bolo {VERSION}")
        return 0

    if args[0] == "-e":
        if len(args) < 2:
            print("bolo: -e needs a program, e.g. -e '1 + 2 |> print'", file=sys.stderr)
            return 2
        source, script_args = args[1], args[2:]
        label = "-e"
        base_dir = Path.cwd()
    else:
        path = args[0]
        try:
            with open(path, encoding="utf-8-sig") as handle:
                source = handle.read()
        except OSError as exc:
            print(f"bolo: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        script_args = args[1:]
        label = path
        base_dir = Path(path).resolve().parent

    interp = Interp()
    interp.base_dir = base_dir
    interp.file_label = label
    interp.source_text = source
    interp.globals.define("args", script_args)
    try:
        interp.run(parse(source))
    except BoloError as err:
        print(format_error(source, label, err), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return interp.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
