"""Checks that the finished task app still works, without opening a window.

The app is a real Bolo program; this test runs it with `show(win)` removed,
then presses its buttons the same way Tk would and reads the results back.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

os.environ.setdefault("BOLO_GUI_SILENT", "1")

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo  # noqa: E402

SOURCE = (APP_DIR / "examples" / "tasks_app.bolo").read_text(encoding="utf-8")
# Drop only the final line, so the window is built but never enters mainloop.
SOURCE = "\n".join(
    line for line in SOURCE.splitlines() if line.strip() != "show(win)"
)


class TaskAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.destroy()
        except Exception as exc:  # noqa: BLE001 - no desktop session
            raise unittest.SkipTest(f"tkinter cannot open a window: {exc}")

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="bolo-tasks-test-"))
        self.previous = os.getcwd()
        os.chdir(self.folder)
        self.interp = self.start_app()
        self.addCleanup(self.finish)

    def finish(self) -> None:
        win = self.interp.globals.get("win")
        win.close()
        os.chdir(self.previous)

    def start_app(self) -> bolo.Interp:
        os.chdir(self.folder)
        interp = bolo.Interp()
        interp.base_dir = self.folder
        with redirect_stdout(io.StringIO()):
            interp.run(bolo.parse(SOURCE))
        return interp

    # -- little helpers -----------------------------------------------------
    def widget(self, name: str):
        return self.interp.globals.get(name)

    def text_of(self, name: str) -> str:
        return self.interp.call_value(self.interp.globals.get("value"), [self.widget(name)])

    def add(self, words: str) -> None:
        self.widget("entry").var.set(words)
        self.widget("add_btn").fire()

    def press(self, name: str, number: str = "") -> None:
        if number:
            self.widget("num_box").var.set(number)
        self.widget(name).fire()

    # -- the checks ---------------------------------------------------------
    def test_starts_empty_and_ready(self) -> None:
        self.assertEqual(self.text_of("status"), "Your list is empty.")
        self.assertIn("No tasks yet", self.text_of("list_box"))
        self.assertEqual(self.text_of("note"), "Ready.")

    def test_adding_tasks_lists_them_in_order(self) -> None:
        self.add("Buy milk")
        self.add("Walk the dog")
        listing = self.text_of("list_box")
        self.assertIn("[ ]  1  Buy milk", listing)
        self.assertIn("[ ]  2  Walk the dog", listing)
        self.assertEqual(self.text_of("status"), "2 open  -  0 done  -  2 in all")
        self.assertEqual(self.text_of("note"), "Added task 2.")
        # the input is emptied, ready for the next task
        self.assertEqual(self.text_of("entry"), "")

    def test_blank_input_is_refused(self) -> None:
        self.add("   ")
        self.assertEqual(self.text_of("note"), "Type a task first, then press Add task.")
        self.assertEqual(self.text_of("status"), "Your list is empty.")

    def test_done_changes_the_mark_and_the_count(self) -> None:
        self.add("Buy milk")
        self.add("Walk the dog")
        self.press("done_btn", "2")
        self.assertIn("[x]  2  Walk the dog", self.text_of("list_box"))
        self.assertEqual(self.text_of("status"), "1 open  -  1 done  -  2 in all")
        self.assertEqual(self.text_of("note"), "Task 2 is done.")

    def test_a_missing_number_gets_a_plain_answer(self) -> None:
        self.add("Buy milk")
        self.press("done_btn", "99")
        self.assertEqual(self.text_of("note"), "There is no task numbered 99.")
        self.press("done_btn", "not a number")
        self.assertEqual(self.text_of("note"), "There is no task numbered 0.")

    def test_delete_removes_one_task(self) -> None:
        self.add("Buy milk")
        self.add("Walk the dog")
        self.press("delete_btn", "1")
        listing = self.text_of("list_box")
        self.assertNotIn("Buy milk", listing)
        self.assertIn("Walk the dog", listing)
        self.assertEqual(self.text_of("note"), "Deleted task 1.")

    def test_the_list_is_saved_and_loaded_again(self) -> None:
        self.add("Buy milk")
        self.add("Walk the dog")
        self.press("done_btn", "1")
        saved = self.folder / "tasks.json"
        self.assertTrue(saved.exists())
        self.assertIn('"Buy milk"', saved.read_text(encoding="utf-8"))

        self.finish()
        self.interp = self.start_app()
        self.assertIn("[x]  1  Buy milk", self.text_of("list_box"))
        self.assertIn("[ ]  2  Walk the dog", self.text_of("list_box"))
        self.assertEqual(self.text_of("status"), "1 open  -  1 done  -  2 in all")

    def test_new_tasks_get_fresh_numbers_after_loading(self) -> None:
        self.add("Buy milk")
        self.finish()
        self.interp = self.start_app()
        self.add("Call Mari")
        self.assertIn("2  Call Mari", self.text_of("list_box"))


if __name__ == "__main__":
    unittest.main()
