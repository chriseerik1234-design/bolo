"""Desktop windows for Bolo, built on tkinter.

This module is imported only the first time a program calls a GUI builtin,
so the command-line interpreter stays light and every non-GUI program keeps
working exactly as before.

The API is deliberately small and flat. A window stacks its children from
top to bottom; `row(parent)` gives you a horizontal strip. Every widget is
a value that can be stored in a box and passed to `value`, `set`, and the
event builtins.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

# When `bolo.py` is run directly it is the __main__ module, so importing
# `bolo` here would load a second copy of the classes and break isinstance.
# Reuse whichever copy is already running this program.
if sys.modules.get("__main__") is not None and hasattr(
    sys.modules["__main__"], "BoloError"
):
    _bolo = sys.modules["__main__"]
else:  # imported normally, e.g. by the learning app
    import bolo as _bolo  # type: ignore[no-redef]

BoloError = _bolo.BoloError
Builtin = _bolo.Builtin
UserFunction = _bolo.UserFunction
describe_type = _bolo.describe_type
to_str = _bolo.to_str
truthy = _bolo.truthy

PAPER = "#f6f5f1"
PANEL = "#ffffff"
INK = "#1d2227"
MUTED = "#6d7178"
ACCENT = "#2f6b4f"
ACCENT_DARK = "#234f3b"
RULE = "#d8d4ca"
FIELD = "#fcfbf8"

UI_FONT = ("Segoe UI", 10)
UI_BOLD = ("Segoe UI Semibold", 10)
HEAD_FONT = ("Segoe UI Semibold", 16)
CODE_FONT = ("Consolas", 10)


def _expect(args: list, lo: int, hi: int, name: str) -> None:
    if not lo <= len(args) <= hi:
        want = str(lo) if lo == hi else f"{lo} to {hi}"
        raise BoloError(f"{name} needs {want} value(s), but got {len(args)}")


def _number(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BoloError(f"{name} needs a number, got {describe_type(value)}")
    return int(value)


def _function(value, name: str):
    if isinstance(value, (UserFunction, Builtin)) or callable(value):
        return value
    raise BoloError(
        f"{name} needs a function, got {describe_type(value)}",
        hint="put the recipe in { } braces, like:  { say(\"clicked\") }",
    )


class Window:
    """A real desktop window. It owns a Tk root and a vertical content area."""

    __bolo_type__ = "window"

    def __init__(self, gui: "Gui", title: str, width: int, height: int):
        self.gui = gui
        self.title = title
        self.closed = False
        self.shown = False
        self.tipped = False

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(280, 180)
        self.root.configure(bg=PAPER)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.content = tk.Frame(self.root, bg=PAPER)
        self.content.pack(fill="both", expand=True, padx=18, pady=16)

    def __str__(self) -> str:
        return f"<window {self.title!r}>"

    __repr__ = __str__

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class Widget:
    """One control, plus the little bit of state needed to read it back."""

    __bolo_type__ = "widget"

    def __init__(
        self,
        gui: "Gui",
        kind: str,
        widget: tk.Widget,
        label: str = "",
        var: tk.Variable | None = None,
        body: tk.Text | None = None,
    ):
        self.gui = gui
        self.kind = kind
        self.widget = widget
        self.label = label
        self.var = var
        self.body = body
        self.actions: list = []

    def __str__(self) -> str:
        if self.label:
            return f"<{self.kind} {self.label!r}>"
        return f"<{self.kind}>"

    __repr__ = __str__

    def fire(self, _event=None) -> None:
        for fn in list(self.actions):
            try:
                self.gui.call_back(fn, self)
            except BoloError as err:
                self.gui.report(err)
            except Exception as exc:  # noqa: BLE001 - shown in a dialog
                self.gui.report(BoloError(str(exc)))


class Gui:
    """One GUI session, tied to one Bolo interpreter."""

    def __init__(self, interp):
        self.interp = interp
        self.win: Window | None = None

    # -- windows ------------------------------------------------------------
    def window(self, args: list) -> Window:
        _expect(args, 0, 3, "window")
        title = to_str(args[0]) if args else "Bolo app"
        width = _number(args[1], "window width") if len(args) > 1 else 440
        height = _number(args[2], "window height") if len(args) > 2 else 330
        if width < 200 or height < 120:
            raise BoloError(
                "a window needs at least 200 by 120 pixels",
                hint="window(\"Title\", 440, 330) is a good starting size",
            )
        if self.win is not None and not self.win.closed:
            raise BoloError(
                "this program already has a window",
                hint="reuse it, or close(win) before opening another",
            )
        self.win = Window(self, title, width, height)
        return self.win

    def _window(self, name: str) -> Window:
        if self.win is None or self.win.closed:
            raise BoloError(
                f"{name} needs an open window",
                hint='make one first:  win = window("My app")',
            )
        return self.win

    def show(self, args: list):
        _expect(args, 1, 1, "show")
        target = args[0]
        if not isinstance(target, Window):
            raise BoloError(f"show needs a window, got {describe_type(target)}")
        if target.closed:
            raise BoloError("that window is already closed")
        if target.shown:
            return None
        target.shown = True
        target.root.deiconify()
        target.root.lift()
        target.root.mainloop()
        return None

    def close(self, args: list):
        _expect(args, 1, 1, "close")
        target = args[0]
        if isinstance(target, Window):
            target.close()
            return None
        if isinstance(target, Widget):
            target.gui._window("close").close()
            return None
        raise BoloError(f"close needs a window or a widget, got {describe_type(target)}")

    def finish(self) -> None:
        """Called when a program ends, to explain a forgotten show(win)."""
        if self.win is not None and not self.win.closed and not self.win.shown:
            if self.win.tipped:
                return
            self.win.tipped = True
            sys.stdout.write(
                "tip: this program made a window but never showed it.\n"
                "     add  show(win)  as the last line to open it.\n"
            )
            sys.stdout.flush()

    def call_back(self, fn, subject) -> None:
        """Call a button/event recipe, handing the widget in as `it`.

        `{ ... }` lambdas always have one value named `it`, while
        `to handler() { ... }` may have none. Support both so beginners can
        use whichever they wrote.
        """
        args = [] if isinstance(fn, UserFunction) and not fn.params else [subject]
        self.interp.call_value(fn, args)

    # -- containers ---------------------------------------------------------
    def _place(self, parent, widget: tk.Widget, kind: str) -> None:
        if isinstance(parent, Widget) and parent.kind == "row":
            widget.pack(side="left", padx=(0, 8), pady=(0, 2))
        elif kind == "textbox":
            widget.pack(fill="both", expand=True, pady=(2, 8))
        else:
            widget.pack(fill="x", pady=(0, 7))

    def _container(self, parent, name: str) -> tk.Widget:
        if isinstance(parent, Window):
            if parent.closed:
                raise BoloError(f"{name} cannot use a closed window")
            return parent.content
        if isinstance(parent, Widget) and parent.kind == "row":
            return parent.widget
        raise BoloError(
            f"{name} needs a window or a row as its first value, "
            f"got {describe_type(parent)}",
            hint="for example:  label(win, \"Hello\")  or  label(my_row, \"Hello\")",
        )

    def row(self, args: list) -> Widget:
        _expect(args, 1, 1, "row")
        parent = self._container(args[0], "row")
        frame = tk.Frame(parent, bg=PAPER)
        self._place(args[0], frame, "row")
        return Widget(self, "row", frame, "row")

    # -- widgets ------------------------------------------------------------
    def label(self, args: list) -> Widget:
        return self._label(args, "label", UI_FONT)

    def heading(self, args: list) -> Widget:
        return self._label(args, "heading", HEAD_FONT)

    def _label(self, args: list, kind: str, font) -> Widget:
        _expect(args, 2, 2, kind)
        parent, text = args
        container = self._container(parent, kind)
        label = to_str(text)
        widget = tk.Label(
            container,
            text=label,
            bg=PAPER,
            fg=INK,
            font=font,
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self._place(parent, widget, kind)
        return Widget(self, kind, widget, label)

    def button(self, args: list) -> Widget:
        _expect(args, 2, 3, "button")
        parent, text = args[0], args[1]
        container = self._container(parent, "button")
        label = to_str(text)
        widget = tk.Button(
            container,
            text=label,
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_DARK,
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=6,
            cursor="hand2",
            font=UI_BOLD,
        )
        self._place(parent, widget, "button")
        result = Widget(self, "button", widget, label)
        if len(args) == 3:
            result.actions.append(_function(args[2], "button"))
            widget.configure(command=result.fire)
        return result

    def input(self, args: list) -> Widget:
        _expect(args, 1, 1, "input")
        parent = args[0]
        container = self._container(parent, "input")
        var = tk.StringVar()
        widget = tk.Entry(
            container,
            textvariable=var,
            font=UI_FONT,
            bg=FIELD,
            fg=INK,
            insertbackground=INK,
            relief="solid",
            borderwidth=1,
        )
        widget.configure(highlightthickness=0)
        self._place(parent, widget, "input")
        return Widget(self, "input", widget, "input", var=var)

    def textbox(self, args: list) -> Widget:
        _expect(args, 1, 3, "textbox")
        parent = args[0]
        lines = _number(args[1], "textbox lines") if len(args) > 1 else 6
        lines = max(2, min(lines, 40))
        editable = truthy(args[2]) if len(args) > 2 else True
        container = self._container(parent, "textbox")

        frame = tk.Frame(
            container, bg=FIELD, highlightbackground=RULE, highlightthickness=1
        )
        body = tk.Text(
            frame,
            height=lines,
            wrap="word",
            font=CODE_FONT,
            bg=FIELD,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
            undo=True,
        )
        if not editable:
            body.configure(state="disabled", takefocus=0, cursor="arrow")
        scroll = tk.Scrollbar(frame, command=body.yview)
        body.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        body.pack(side="left", fill="both", expand=True)

        self._place(parent, frame, "textbox")
        return Widget(self, "textbox", frame, "textbox", body=body)

    def check(self, args: list) -> Widget:
        _expect(args, 2, 2, "check")
        parent, text = args
        container = self._container(parent, "check")
        label = to_str(text)
        var = tk.BooleanVar()
        widget = tk.Checkbutton(
            container,
            text=label,
            variable=var,
            bg=PAPER,
            fg=INK,
            activebackground=PAPER,
            activeforeground=INK,
            anchor="w",
            font=UI_FONT,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self._place(parent, widget, "check")
        return Widget(self, "check", widget, label, var=var)

    # -- values -------------------------------------------------------------
    def value(self, args: list):
        _expect(args, 1, 1, "value")
        target = args[0]
        if isinstance(target, Window):
            return target.title
        if not isinstance(target, Widget):
            raise BoloError(
                f"value needs a widget or a window, got {describe_type(target)}"
            )
        if target.kind in ("label", "button", "heading"):
            return str(target.widget.cget("text"))
        if target.kind == "input":
            return target.var.get()
        if target.kind == "textbox":
            return target.body.get("1.0", "end-1c")
        if target.kind == "check":
            return bool(target.var.get())
        raise BoloError(f"value cannot read a {target.kind}")

    def set(self, args: list):
        _expect(args, 2, 2, "set")
        target, value = args
        if isinstance(target, Window):
            target.title = to_str(value)
            target.root.title(target.title)
            return None
        if not isinstance(target, Widget):
            raise BoloError(
                f"set needs a widget or a window, got {describe_type(target)}"
            )
        text = to_str(value)
        if target.kind in ("label", "button", "heading"):
            target.widget.configure(text=text)
            target.label = text
        elif target.kind == "input":
            target.var.set(text)
        elif target.kind == "textbox":
            was_disabled = str(target.body.cget("state")) == "disabled"
            if was_disabled:
                target.body.configure(state="normal")
            target.body.delete("1.0", "end")
            target.body.insert("1.0", text)
            if was_disabled:
                target.body.configure(state="disabled")
        elif target.kind == "check":
            target.var.set(truthy(value))
        else:
            raise BoloError(f"set cannot change a {target.kind}")
        return None

    def add_line(self, args: list):
        _expect(args, 2, 2, "add_line")
        target, value = args
        if not isinstance(target, Widget) or target.kind != "textbox":
            raise BoloError("add_line needs a textbox")
        was_disabled = str(target.body.cget("state")) == "disabled"
        if was_disabled:
            target.body.configure(state="normal")
        target.body.insert("end", to_str(value) + "\n")
        target.body.see("end")
        if was_disabled:
            target.body.configure(state="disabled")
        return None

    def clear(self, args: list):
        _expect(args, 1, 1, "clear")
        target = args[0]
        if not isinstance(target, Widget):
            raise BoloError(f"clear needs a widget, got {describe_type(target)}")
        if target.kind in ("label", "button", "heading"):
            target.widget.configure(text="")
            target.label = ""
        elif target.kind == "input":
            target.var.set("")
        elif target.kind == "textbox":
            was_disabled = str(target.body.cget("state")) == "disabled"
            if was_disabled:
                target.body.configure(state="normal")
            target.body.delete("1.0", "end")
            if was_disabled:
                target.body.configure(state="disabled")
        elif target.kind == "check":
            target.var.set(False)
        else:
            raise BoloError(f"clear cannot empty a {target.kind}")
        return None

    # -- events -------------------------------------------------------------
    def on_click(self, args: list):
        _expect(args, 2, 2, "on_click")
        target, fn = args[0], _function(args[1], "on_click")
        if not isinstance(target, Widget) or target.kind not in ("button", "check"):
            raise BoloError("on_click needs a button or a check")
        target.actions.append(fn)
        if target.kind == "button":
            target.widget.configure(command=target.fire)
        else:
            target.widget.configure(command=target.fire)
        return None

    def on_change(self, args: list):
        _expect(args, 2, 2, "on_change")
        target, fn = args[0], _function(args[1], "on_change")
        if not isinstance(target, Widget):
            raise BoloError(
                f"on_change needs an input, textbox or check, got {describe_type(target)}"
            )
        if target.kind == "input":
            target.actions.append(fn)
            target.widget.bind("<KeyRelease>", target.fire)
            target.widget.bind("<Return>", target.fire)
        elif target.kind == "textbox":
            target.actions.append(fn)
            target.body.bind("<KeyRelease>", target.fire)
        elif target.kind == "check":
            target.actions.append(fn)
            target.widget.configure(command=target.fire)
        else:
            raise BoloError("on_change needs an input, textbox or check")
        return None

    def later(self, args: list):
        _expect(args, 3, 3, "later")
        target, ms, fn = args[0], _number(args[1], "later"), _function(args[2], "later")
        window = self._window("later") if not isinstance(target, Window) else target
        if window.closed:
            raise BoloError("later cannot use a closed window")
        delay = max(0, ms)

        def once() -> None:
            if window.closed:
                return
            try:
                self.call_back(fn, window)
            except BoloError as err:
                self.report(err)

        window.root.after(delay, once)
        return None

    def every(self, args: list):
        _expect(args, 3, 3, "every")
        target, ms, fn = args[0], _number(args[1], "every"), _function(args[2], "every")
        window = self._window("every") if not isinstance(target, Window) else target
        if window.closed:
            raise BoloError("every cannot use a closed window")
        delay = max(1, ms)

        def tick() -> None:
            if window.closed:
                return
            try:
                self.call_back(fn, window)
            except BoloError as err:
                self.report(err)
            if not window.closed:
                window.root.after(delay, tick)

        window.root.after(delay, tick)
        return None

    # -- dialogs and files --------------------------------------------------
    def _dialog_parent(self, name: str):
        return self.win.root if self.win is not None and not self.win.closed else None

    def alert(self, args: list):
        _expect(args, 1, 2, "alert")
        message = to_str(args[0])
        title = to_str(args[1]) if len(args) > 1 else "Bolo"
        messagebox.showinfo(title, message, parent=self._dialog_parent("alert"))
        return None

    def ask(self, args: list):
        _expect(args, 1, 2, "ask")
        message = to_str(args[0])
        title = to_str(args[1]) if len(args) > 1 else "Bolo"
        return bool(
            messagebox.askyesno(title, message, parent=self._dialog_parent("ask"))
        )

    def choose_file(self, args: list):
        _expect(args, 0, 1, "choose_file")
        title = to_str(args[0]) if args else "Choose a file"
        chosen = filedialog.askopenfilename(
            title=title, parent=self._dialog_parent("choose_file")
        )
        return chosen or None

    def save_file(self, args: list):
        _expect(args, 0, 1, "save_file")
        title = to_str(args[0]) if args else "Save as"
        chosen = filedialog.asksaveasfilename(
            title=title, parent=self._dialog_parent("save_file")
        )
        return chosen or None

    # -- errors -------------------------------------------------------------
    def report(self, err: BoloError) -> None:
        text = err.message
        if err.hint:
            text += "\n\n" + err.hint
        if os.environ.get("BOLO_GUI_SILENT"):
            print(f"bolo: {text}", file=sys.stderr)
            return
        try:
            messagebox.showerror("Bolo app", text, parent=self._dialog_parent("error"))
        except Exception:  # noqa: BLE001 - no display left to report to
            print(f"bolo: {text}", file=sys.stderr)
