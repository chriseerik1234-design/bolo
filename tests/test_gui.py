"""Tests for Bolo's desktop-app builtins.

They create real Tk windows but never enter the event loop, so they finish
on their own. When no display is available the whole class is skipped.
"""
from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout

os.environ.setdefault("BOLO_GUI_SILENT", "1")

import bolo  # noqa: E402


def make_interp() -> bolo.Interp:
    return bolo.Interp()


def run(interp: bolo.Interp, source: str) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        interp.run(bolo.parse(source))
    return buffer.getvalue()


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.destroy()
        except Exception as exc:  # noqa: BLE001 - no desktop session
            raise unittest.SkipTest(f"tkinter cannot open a window: {exc}")

    def tearDown(self) -> None:
        win = getattr(self, "win", None)
        if win is not None:
            win.close()

    def test_window_and_widgets_are_values(self) -> None:
        interp = make_interp()
        run(
            interp,
            'win = window("Test", 420, 300)\n'
            'heading(win, "Hello")\n'
            'name = input(win)\n'
            'result = label(win, "waiting")\n'
            'set(name, "Mari")\n'
            'say(value(name))\n'
            'say(type(win))\n'
            'say(type(result))\n',
        )
        self.win = interp.globals.get("win")
        self.assertEqual(run(interp, "say(value(name))\n").strip(), "Mari")
        self.assertEqual(run(interp, "say(type(win))\n").strip(), "window")
        self.assertEqual(run(interp, "say(type(result))\n").strip(), "widget")

    def test_button_runs_a_lambda_with_it(self) -> None:
        interp = make_interp()
        run(
            interp,
            'win = window("Test")\n'
            'name = input(win)\n'
            'result = label(win, "waiting")\n'
            'b = button(win, "Greet", { set(result, "Hi " + value(name)) })\n'
            'set(name, "Mari")\n',
        )
        self.win = interp.globals.get("win")
        button = interp.globals.get("b")
        result = interp.globals.get("result")
        button.widget.invoke()
        self.assertEqual(result.widget.cget("text"), "Hi Mari")

    def test_button_accepts_a_function_with_no_parameters(self) -> None:
        interp = make_interp()
        run(
            interp,
            'win = window("Test")\n'
            'result = label(win, "waiting")\n'
            'b = button(win, "Go")\n'
            'to reset() { set(result, "reset") }\n'
            'on_click(b, reset)\n',
        )
        self.win = interp.globals.get("win")
        interp.globals.get("b").widget.invoke()
        self.assertEqual(interp.globals.get("result").widget.cget("text"), "reset")

    def test_textbox_append_and_clear(self) -> None:
        interp = make_interp()
        run(
            interp,
            'win = window("Test")\n'
            'box = textbox(win, 4)\n'
            'add_line(box, "one")\n'
            'add_line(box, "two")\n'
            'say(value(box))\n'
            'clear(box)\n'
            'say("[" + value(box) + "]")\n',
        )
        self.win = interp.globals.get("win")
        output = run(interp, 'say("[" + value(box) + "]")\n')
        self.assertEqual(output.strip(), "[]")
        self.assertEqual(
            interp.globals.get("box").body.get("1.0", "end-1c"), ""
        )

    def test_checkbox_and_set(self) -> None:
        interp = make_interp()
        run(
            interp,
            'win = window("Test")\n'
            'agree = check(win, "I agree")\n'
            'set(agree, true)\n'
            'say(value(agree))\n',
        )
        self.win = interp.globals.get("win")
        self.assertTrue(interp.globals.get("agree").var.get())

    def test_a_window_that_is_never_shown_gets_a_tip(self) -> None:
        interp = make_interp()
        output = run(interp, 'win = window("Test")\nlabel(win, "hi")\n')
        self.win = interp.globals.get("win")
        self.assertIn("show(win)", output)

    def test_closing_removes_the_window(self) -> None:
        interp = make_interp()
        run(interp, 'win = window("Test")\nclose(win)\n')
        self.assertTrue(interp.globals.get("win").closed)
        self.win = None

    def test_bad_widget_parent_is_explained(self) -> None:
        interp = make_interp()
        with self.assertRaises(bolo.BoloError) as caught:
            run(interp, 'label("not a window", "hi")\n')
        self.assertIn("window or a row", caught.exception.message)


if __name__ == "__main__":
    unittest.main()
